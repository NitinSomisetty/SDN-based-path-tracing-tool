# SDN Path Tracing Tool (OpenFlow / Ryu / Mininet)

"When a packet travels through a network, which path did it take?"


The switch asks the controller via a packet_in event. The controller replies with a flow rule — essentially saying "for all future packets like this one, do X". After that, the switch handles it alone without asking again.


Mininet says:  "create a network with 3 switches"
OVS does:      actually runs 3 real software switches on your Linux machine
Ryu talks to:  those OVS switches via OpenFlow


Your Python code (Ryu) 
    ↓ speaks OpenFlow
Open vSwitch (the actual switch engine)
    ↓ managed by
Mininet (just the topology builder)


python3.10 -m venv ~/sdn-env
source ~/sdn-env/bin/activate


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

### Scenario 2: Blocked Traffic (H2 → H4)
```
mininet> h2 ping -c 3 h4
```
**Expected:** 100% packet loss. Flow rule `DROP` installed at startup blocks H2→H4.

### View Flow Tables
```bash
mininet> sh ovs-ofctl dump-flows s1 -O OpenFlow13
```

### Performance Test
```bash
mininet> iperf h1 h4
```

## Proof of Execution (Screenshots to capture)
1. `pingall` — baseline connectivity
2. Controller terminal showing path trace logs
3. `ovs-ofctl dump-flows s1/s2/s3` — flow tables
4. `h2 ping h4` showing 100% loss
5. `iperf h1 h4` bandwidth output

## Key Concepts Learned
- **packet_in**: event fired when no flow rule matches a packet
- **MAC learning**: controller builds a MAC→port table dynamically  
- **Flow rules**: (match, action) pairs installed on switches
- **Path tracing**: logging each switch a packet traverses
- **OpenFlow 1.3**: the protocol between controller and switches

## File Structure
```
sdn-path-tracer/
├── controller.py    # Ryu controller with path tracing logic
├── topology.py      # Mininet custom topology (3 switches, 4 hosts)
├── run_demo.sh      # Quick-start guide
└── README.md        # This file
```