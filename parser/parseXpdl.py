import xml.etree.ElementTree as et
from collections import defaultdict
import sys  

def parseXpdl(filePath):
    tree = et.parse(filePath)
    root = tree.getroot()
    counts = defaultdict(int)
    ns = {
        'xpdl': 'http://www.wfmc.org/2009/XPDL2.2'
    }

    for child in root:
        print("Parent 1: ", child.tag)
        for child1 in child:
            print("Parent 2: ", child1.tag)
            for child2 in child1:
                print("Parent 3: ", child2.tag)
                for child3 in child2:
                    print("Parent 4: ", child3.tag)
                

    for task in root.findall(".//xpdl:Task", ns):
        counts['tasks'] += 1
    
    for event in root.findall(".//xpdl:Event", ns):
        counts['events'] += 1

    for startEvent in root.findall(".//xpdl:StartEvent", ns):
        counts['event_Start'] += 1
    
    for endEvent in root.findall(".//xpdl:EndEvent", ns):
        counts['event_End'] += 1

    for gateway in root.findall(".//xpdl:Route", ns):
        gatewayType = gateway.get("GatewayType", "Undefined Type")
        counts['gateway'] += 1
        counts[f'gateway_{gatewayType}'] += 1
    
    for pool in root.findall(".//xpdl:Pool", ns):
        counts['pools'] += 1
    for lane in root.findall(".//xpdl:Lane", ns):
        counts['lanes'] += 1
    
    for key, value in counts.items():
        print(f"{key}: {value}")

if __name__ == '__main__':
    if (len(sys.argv) < 2):
        print("Please provide the path to an XPDL file as a command-line argument.")
        sys.exit(1)
    filePath = sys.argv[1]
    parseXpdl(filePath)
