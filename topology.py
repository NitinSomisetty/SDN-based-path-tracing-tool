from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel

class PathTracingTopo(Topo):
    # Linear 3-switch topology with 4 hosts.

    def build(self):
        # Create switches and assign dpid manually

        s1 = self.addSwitch('s1', dpid='0000000000000001')
        s2 = self.addSwitch('s2', dpid='0000000000000002')
        s3 = self.addSwitch('s3', dpid='0000000000000003')

        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
        h3 = self.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
        h4 = self.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')

        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(s1, s2)
        self.addLink(s2, s3)
        self.addLink(s3, h3)
        self.addLink(s3, h4)
        
def run():
    setLogLevel('info')
    topo = PathTracingTopo()
    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653)
    )
    net.start()
    print("Your network has started!")
    CLI(net)
    net.stop()

topos = {'pathtracingtopo': PathTracingTopo}

if __name__ == '__main__':
    run()