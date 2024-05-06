import xml.etree.ElementTree as et
import random
import sys

def addActivityTime(inputFile, outputFile):
    ns = {
        'xpdl': 'http://www.wfmc.org/2009/XPDL2.2',
        'bpmn': 'http://www.omg.org/spec/BPMN/20080501/BPMN20.xsd'
    }
    tree = et.parse(inputFile)
    root = tree.getroot()

    for task in root.findall(".//xpdl:Activity", ns):
        duration = random.randint(5, 15)
        task.set("Duration", str(duration))
    
    tree.write(outputFile)

if __name__ == '__main__':
    if (len(sys.argv) < 3):
        print("Please provide the path to an XPDL file as a command-line argument.")
        sys.exit(1)
    input = sys.argv[1]
    output = sys.argv[2]
    addActivityTime(input, output)