from ryu.base import app_manager  # a class like Topo
from ryu.controller import ofp_event # open flow events
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER  # states a switch goes through
from ryu.controller.handler import set_ev_cls  # "call this function when this event happens"
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet  #Parses raw packet bytes into readable fields
import logging
import time
from collections import defaultdict  #auto creates missing keys with default values, useful for our MAC learning and path logging dictionaries


class PathTracingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):

        super(PathTracingController, self).__init__(*args, **kwargs)
        self.mac_to_port = defaultdict(dict) #nested dict: {dpid: {mac: port}} to remember which MAC is on which port for each switch
        self.path_log = defaultdict(list) #stores the path history for each flow, keyed by (src_mac, dst_mac) tuple
        self.switch_names = {0x1: 'S1', 0x2: 'S2', 0x3: 'S3'}
        
        self.host_names = {
            '00:00:00:00:00:01': 'H1',
            '00:00:00:00:00:02': 'H2',
            '00:00:00:00:00:03': 'H3',
            '00:00:00:00:00:04': 'H4',
        }



    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER) #ofp_event.EventOFPSwitchFeatures means "when a switch connects and sends its features, call this function".
    def switch_features_handler(self, event_handler):
        datapath = event_handler.msg.datapath #switch object extracted from openflow message
        ofproto = datapath.ofproto #contains constants for OpenFlow 
        parser = datapath.ofproto_parser # used to construct OpenFlow messages in the correct format
        dpid = datapath.id # switch ID

        # Table-miss rule: any unmatched packet -> send to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]

        self._add_flow(datapath, priority=0, match=match, actions=actions) #priority 0

        # Block rule: H2 → H4 gets dropped (priority 10 beats forwarding rules)
        block_match = parser.OFPMatch(
            eth_src='00:00:00:00:00:02',
            eth_dst='00:00:00:00:00:04'
        )
        self._add_flow(datapath, priority=10, match=block_match, actions=[]) #drop action is just an empty list of actions

        # Block rule: H4 → H2 gets dropped (reverse direction)
        block_match_reverse = parser.OFPMatch(
            eth_src='00:00:00:00:00:04',
            eth_dst='00:00:00:00:00:02'
        )
        self._add_flow(datapath, priority=10, match=block_match_reverse, actions=[]) #drop action is just an empty list of actions

        
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event_handler):
        msg = event_handler.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        in_port = msg.match['in_port']  # the port on which this packet arrived at the switch, used for learning and forwarding decisions

        # Parse the Ethernet frame
        pkt = packet.Packet(msg.data) # parses the packet to read properly
        eth = pkt.get_protocols(ethernet.ethernet)[0] 

        # Ignores LLPD noise
        if eth.ethertype == 0x88cc:
            return

        src_mac = eth.src # source MAC address, used for learning and path tracing
        dst_mac = eth.dst # destination MAC address, used for forwarding and path tracing
        flow_id = (src_mac, dst_mac)

        # PATH TRACING: Initialize with source host
        if len(self.path_log[flow_id]) == 0:
            self.path_log[flow_id].append({
                'switch': self.host_names.get(src_mac, src_mac)
            })

        # MAC LEARNING: remember which port this MAC came from
        self.mac_to_port[dpid][src_mac] = in_port

# Example: If H1 (MAC 00:00:00:00:00:01) sends a packet that arrives on S1's port 1, 
# this stores: mac_to_port[S1]['00:00:00:00:00:01'] = 1

        # FORWARDING DECISION
        if dst_mac in self.mac_to_port[dpid]: # if we know where the destination MAC is, send it there
            out_port = self.mac_to_port[dpid][dst_mac] # Now when we forward to H1 from S1, we use out_port = 1
        else:
            out_port = ofproto.OFPP_FLOOD # if we don't know, flood to all ports except the one it came in on

        # Avoid logging incomplete noisy paths (before path tracing)
        if out_port == ofproto.OFPP_FLOOD:
            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)
            return

        # PATH TRACING: log this switch (prevent duplicates)
        current_switch = self.switch_names.get(dpid, f'SW-{dpid}')
        if not self.path_log[flow_id] or \
           self.path_log[flow_id][-1]['switch'] != current_switch:
            self.path_log[flow_id].append({
                'switch': current_switch,
                'in_port': in_port,
                'time': time.time()
            })

        # Print path when packet reaches destination
        path = self.path_log[flow_id]
        if len(path) >= 2:
            # Add destination host
            dst_name = self.host_names.get(dst_mac, dst_mac)
            if path[-1]['switch'] != dst_name:
                path.append({'switch': dst_name})
            
            # Print formatted path
            path_str = " → ".join([h['switch'] for h in path])
            src_name = self.host_names.get(src_mac, src_mac)
            print(f"[PATH] {src_name} → {dst_name}: {path_str}")
            
            # Reset path after printing
            self.path_log[flow_id] = []


        actions = [parser.OFPActionOutput(out_port)] 
        if out_port != ofproto.OFPP_FLOOD:
            # Only match on MAC addresses, not in_port (needed for bidirectional traffic like iperf)
            match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)

            self._add_flow(datapath, priority=1, match=match, actions=actions)

        # Send this packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        datapath.send_msg(out)
        
    def _add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)