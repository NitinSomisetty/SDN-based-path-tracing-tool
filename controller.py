from ryu.base import app_manager  # a class like Topo
from ryu.controller import ofp_event # open flow events
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER  # states a switch goes through
from ryu.controller.handler import set_ev_cls  # "call this function when this event happens"
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
import logging
import time
from collections import defaultdict

class PathTracingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PathTracingController, self).__init__(*args, **kwargs)
        self.mac_to_port = defaultdict(dict)
        self.path_log = defaultdict(list)
        self.switch_names = {0x1: 'S1', 0x2: 'S2', 0x3: 'S3'}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath #switch object
        ofproto = datapath.ofproto #contains constants for OpenFlow like OFPP_CONTROLLER (the port number that means "send to controller") and OFPP_FLOOD (send out all ports).
        parser = datapath.ofproto_parser
        dpid = datapath.id #switch ID

        # Table-miss rule: any unmatched packet → send to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, priority=0, match=match, actions=actions)

        # Block rule: H2 → H4 gets dropped (priority 10 beats forwarding rules)
        block_match = parser.OFPMatch(
            eth_src='00:00:00:00:00:02',
            eth_dst='00:00:00:00:00:04'
        )
        self._add_flow(datapath, priority=10, match=block_match, actions=[])

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        in_port = msg.match['in_port']

        # Parse the Ethernet frame
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Ignore LLDP noise
        if eth.ethertype == 0x88cc:
            return

        src_mac = eth.src
        dst_mac = eth.dst
        flow_id = (src_mac, dst_mac)

        # PATH TRACING: log this switch
        self.path_log[flow_id].append({
            'switch': self.switch_names.get(dpid, f'SW-{dpid}'),
            'in_port': in_port,
            'time': time.time()
        })

        # Print path when packet crosses multiple switches
        path = self.path_log[flow_id]
        if len(path) >= 2:
            path_str = " → ".join([h['switch'] for h in path])
            print(f"[PATH] {src_mac[-5:]} → {dst_mac[-5:]}: {path_str}")

        # MAC LEARNING: remember which port this MAC came from
        self.mac_to_port[dpid][src_mac] = in_port

        # FORWARDING DECISION
        if dst_mac in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow rule if we know the port
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac, eth_src=src_mac)
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