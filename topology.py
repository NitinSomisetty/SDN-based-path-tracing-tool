from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel


"""

SDN Path Tracing Tool - Custom Mininet Topology
Creates: 3 switches (S1, S2, S3) in a linear chain + 4 hosts
  H1 -- S1 -- S2 -- S3 -- H4
         |           |
         H2          H3

"""


class PathTracingTopo(Topo): 
    # we defin a custom topology class that inherits from the Topo class provided by Mininet.

    def build(self):

        # self is a reference to the topology object

        # Create switches and assign dpid manually
        s1 = self.addSwitch('s1', dpid='0000000000000001')
        s2 = self.addSwitch('s2', dpid='0000000000000002')
        s3 = self.addSwitch('s3', dpid='0000000000000003')

#now lets store the layer 2 and layer 3 info to some random python var
        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01') # assigning mac address and names
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')  # /24 is a network prefix, same as subnet mask
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
    topo = PathTracingTopo() #* create an instance of the PathTracingTopo class, which defines our custom network topology.
    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653) #connect to the remote controller running on localhost at port 6653 ( RYU)
    )
    net.start()
    print("Your network has started!")
    CLI(net) #mininet terminal opens
    net.stop()

topos = {'pathtracingtopo': PathTracingTopo} # This line creates a dictionary called topos that maps the string 'pathtracingtopo' to the PathTracingTopo class. 
#This allows us to specify our custom topology when running Mininet from the command line.

if __name__ == '__main__':
    run()