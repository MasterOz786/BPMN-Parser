import xml.etree.ElementTree as et
import networkx as nx

def calculateCT(filePath):
    ns = {
        'xpdl': 'http://www.wfmc.org/2009/XPDL2.2',
        'bpmn': 'http://www.omg.org/spec/BPMN/20080501/BPMN20.xsd'
    }
    tree = et.parse(filePath)
    root = tree.getroot()
    process = root.find(".//xpdl:WorkflowProcess", ns)
    graph = nx.DiGraph()

    activities = process.find(".//xpdl:Activities", ns).findall(".//xpdl:Activity", ns)
    for activity in activities:
        id = activity.get("Id")
        duration = activity.get("Duration")
        graph.add_node(id, duration=duration)
    
    transitions = process.find(".//xpdl:Transitions", ns).findall(".//xpdl:Transition", ns)
    for transition in transitions:
        fromId = transition.get("From")
        toId = transition.get("To")
        graph.add_edge(fromId, toId)
    
    longestPath = nx.dag_longest_path(graph, weight="duration")
    cycleTime = 0
    for node in longestPath:
        cycleTime += int(graph.nodes[node]["duration"])
    return cycleTime

print(calculateCT('output.xpdl'))
