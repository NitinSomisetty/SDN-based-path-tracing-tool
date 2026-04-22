# SDN Path Tracing Tool (OpenFlow / Ryu / Mininet)

"When a packet travels through a network, which path did it take?"


The switch asks the controller via a packet_in event. The controller replies with a flow rule — essentially saying "for all future packets like this one, do X". After that, the switch handles it alone without asking again.

``` bash
Mininet says:  "create a network with 3 switches"
OVS does:      actually runs 3 real software switches on your Linux machine
Ryu talks to:  those OVS switches via OpenFlow
```

Your Python code (Ryu) 
    -> speaks OpenFlow ->
Open vSwitch (the actual switch engine)
    -> managed by ->
Mininet (just the topology builder)


## Problem Statement
Implement an SDN-based path tracing tool using Mininet and the Ryu OpenFlow controller. The tool identifies and displays the exact path taken by packets through the network, implements flow rules for forwarding and blocking, and validates network behavior through two distinct scenarios.

## Architecture
```
             [Ryu Controller]
           /        |        \
        (OpenFlow 1.3 channels)
         /          |          \
       [S1]  ---  [S2]  ---  [S3]
      /    \                 /    \
    H1      H2            H3      H4

Path trace example: H1 → S1 → S2 → S3 → H4
```

## Setup & Execution

### Prerequisites
```bash
# Install Ryu
pip install ryu

# Mininet (Ubuntu/Debian)
sudo apt-get install mininet

# Open vSwitch (usually bundled with Mininet)
sudo apt-get install openvswitch-switch
```

### Virtual Environment (recommended)
```bash
python3.10 -m venv ~/sdn-env38
source ~/sdn-env38/bin/activate
```

### Running the Project

**Terminal 1 — Start the controller:**
```bash
ryu-manager controller.py --observe-links
```

**Terminal 2 — Start the topology:**
```bash
sudo mn --custom topology.py \
        --topo pathtracingtopo \
        --controller remote \
        --switch ovsk,protocols=OpenFlow13
```

      ### Main Validation Flow (Mininet CLI)
      ```bash
      mininet> h1 ping -c 3 h4
      mininet> h1 ping -c 3 h2
      mininet> h2 ping -c 3 h4
      mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
      mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s2
      mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s3
      mininet> h2 iperf -s &
      mininet> h1 iperf -c 10.0.0.2 -t 5
      mininet> pingall
      ```

## Scenarios & Expected Output

### Scenario 1: Allowed Traffic (H1 → H4)
```
mininet> h1 ping -c 3 h4
```
**Controller logs show:**
```
[TRACE] Packet 00:01 → 00:04 arrived at S1 port 1
[TRACE] Packet 00:01 → 00:04 arrived at S2 port 1
[TRACE] Packet 00:01 → 00:04 arrived at S3 port 3
[PATH]  00:01 → 00:04: S1 → S2 → S3
[RULE]  Installed on S1: in=1, dst=00:04 → port 3
```
You may also see host-level formatted traces from the controller, for example:
```
[PATH] H1 → H4: H1 → S1 → S2 → S3 → H4
```

### Scenario 2: Blocked Traffic (H2 → H4)
```
mininet> h2 ping -c 3 h4
```
**Expected:** 100% packet loss. Flow rule `DROP` installed at startup blocks H2→H4.

### View Flow Tables
```bash
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s2
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s3
```
Expected flow-table pattern:
- `priority=10` drop rules for H2→H4 and H4→H2
- `priority=1` learned forwarding rules for allowed traffic
- `priority=0` table-miss rule (send unmatched packets to controller)

### Performance Test
```bash
mininet> h2 iperf -s &
mininet> h1 iperf -c 10.0.0.2 -t 5
```
Expected: TCP bandwidth report from iperf client.

### Global Connectivity Snapshot
```bash
mininet> pingall
```
Expected: all intended pairs reachable except the blocked H2↔H4 pair.


## Key Concepts Learned
- **packet_in**: event fired when no flow rule matches a packet
- **MAC learning**: controller builds a MAC→port table dynamically  
- **Flow rules**: (match, action) pairs installed on switches
- **Path tracing**: logging each switch a packet traverses
- **OpenFlow 1.3**: the protocol between controller and switches

## Core SDN Theory 

### Control Plane vs Data Plane
- **Data plane** (switches): forwards packets
- **Control plane** (Ryu): decides policy and installs rules

### OpenFlow Rule Priority Model
- Higher priority rules win over lower priority rules
- In this project:
  - `priority=10`: policy drop rules (H2↔H4)
  - `priority=1`: learned forwarding rules
  - `priority=0`: table-miss rule to controller

### Why `packet_in` Occurs
When a packet does not match existing entries, switch sends `packet_in` to controller. Controller then learns source location, decides output, and installs a flow for future packets.

### Path Tracing Logic
Each flow is tracked by `(src_mac, dst_mac)`. As packets move, switch visits are logged and printed as a path when destination is reached.


## Limitations and Future Improvements

Current limitations:
- Path tracing is event/log based, not packet-capture level
- Static topology (3 switches, 4 hosts)
- Blocking policy is preconfigured by MAC pair

Future improvements:
- Dynamic shortest-path routing from discovered topology
- Dashboard/REST API for real-time path visualization
- Export traces to CSV/JSON
- Add unit/integration tests for controller behavior

## File Structure
```
sdn-path-tracer/
├── controller.py    # Ryu controller with path tracing logic
├── topology.py      # Mininet custom topology (3 switches, 4 hosts)
├── run_demo.sh      # Quick-start guide
└── README.md        # This file
```