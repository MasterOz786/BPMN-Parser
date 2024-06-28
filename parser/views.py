from collections import defaultdict
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.files import File
from django.core.files.storage import FileSystemStorage
import xml.etree.ElementTree as ElTr
import os
import random
from . import forms

xmlpath = "static/upload/bpmn.xml"

def readfile(request):
    f = open(xmlpath, "r")
    if f.mode == 'r':
        contents = f.read()
    return contents

def addActivityTime(tree, filepath):
    ns = {
        'xpdl': 'http://www.wfmc.org/2009/XPDL2.2',
        # 'bpmn': 'http://www.omg.org/spec/BPMN/20080501/BPMN20.xsd'
        'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'
    }
    
    root = tree.getroot()        
        
    # for xpdl
    namespaces = {'default': ns.get('xpdl')}

    # Update activities with random duration between 5 and 15 minutes, excluding gateways
    print("Activities and their assigned durations:")
    for activity in root.findall('.//default:Activity', namespaces):
        if activity.find('.//default:Route', namespaces) is None:
            # This is not a gateway, so assign a durations
            duration = random.randint(5, 15)
            activity.set('Duration', str(duration))  # Setting duration directly on the <Activity> tag
            print(f"Activity '{activity.get('Name')}' (ID: {activity.get('Id')}): Duration set to {duration} minutes")

    # Assign probabilities only to transitions connected to gateways
    print("\nTransitions from gateways and their assigned probabilities:")
    for gateway in root.findall('.//default:Activity/default:Route/..', namespaces):
        for transition in root.findall(f'.//default:Transition[@From="{gateway.get("Id")}"]', namespaces):
            probability = round(random.random(), 2)
            transition.set('Probability', str(probability))  # Setting probability directly on the <Transition> tag
            print(f"Transition from Gateway '{gateway.get('Name')}' (ID: {gateway.get('Id')}) to Activity ID {transition.get('To')}: Probability set to {probability}")

    # only get the filename without extension
    filename = os.path.basename(filepath).split('.')[0] + '_output.xpdl'
    # Save the modified XML to the specified output path
    ElTr.register_namespace('', 'http://www.wfmc.org/2009/XPDL2.2')
    tree.write(filename)
    print(f"\nXPDL file updated and saved as " + filename, end='\n\n')
    
    return tree

def calculateCT(root):
    # Define XML namespaces to search tags properly
    namespaces = {'ns0': 'http://www.wfmc.org/2009/XPDL2.2'}

    # Collect all activities and their durations
    activities = {}
    for activity in root.findall('.//ns0:Activity', namespaces):
        duration = activity.get('Duration')
        if duration:
            activities[activity.get('Id')] = int(duration)
        else:
            activities[activity.get('Id')] = 0  # Assigning zero if no duration is found

    # Function to recursively calculate the cycle time
    def calculate_path_time(activity_id, accumulated_probability=1.0):
        current_duration = activities.get(activity_id, 0)
        transitions = root.findall(f'.//ns0:Transition[@From="{activity_id}"]', namespaces)

        if not transitions:
            return current_duration * accumulated_probability

        times = []
        for transition in transitions:
            next_id = transition.get('To')
            probability = transition.get('Probability', '1.0')  # Default probability is 1.0
            prob_value = float(probability)

            next_time = calculate_path_time(next_id, accumulated_probability * prob_value)
            times.append(next_time)

        # For parallel processes, take the maximum time; otherwise, sum up the times
        if len(transitions) > 1:
            total_time = current_duration + max(times)
        else:
            total_time = current_duration + sum(times)

        return total_time

    # Start calculation from the first activity found in the document
    start_activity_id = root.find('.//ns0:Activity', namespaces).get('Id')
    total_cycle_time = calculate_path_time(start_activity_id)
    print(f"Total cycle time for the process is {total_cycle_time} minutes")

def parseXPDL(tree):
    counts = defaultdict(int)
    root = tree.getroot()
    
    addActivityTime(tree)
    
    ns = {
        'xpdl': 'http://www.wfmc.org/2009/XPDL2.2'
    }

    for task in root.findall(".//xpdl:TaskUser", ns):
        counts['User Tasks'] += 1
    for task in root.findall(".//xpdl:TaskService", ns):
        counts['Service Tasks'] += 1
    for task in root.findall(".//xpdl:TaskScript", ns):
        counts['Script Tasks'] += 1
    for task in root.findall(".//xpdl:TaskManual", ns):
        counts['Manual Tasks'] += 1

    for startEvent in root.findall(".//xpdl:StartEvent", ns):
        counts['Start Events'] += 1
    
    for endEvent in root.findall(".//xpdl:EndEvent", ns):
        counts['End Events'] += 1

    for interEvent in root.findall(".//xpdl:IntermediateEvent", ns):
        counts['Intermediate Events'] += 1

    for gateway in root.findall(".//xpdl:Route", ns):
        counts['Gateways'] += 1
        if gateway.get('Type') == 'XOR':
            counts['XOR Gateway'] += 1
        elif gateway.get('Type') == 'AND':
            counts['AND Gateway'] += 1
        elif gateway.get('Type') == 'OR':
            counts['OR Gateway'] += 1
    
    for datastore in root.findall(".//xpdl:DataStoreReference", ns):
        counts['Data Objects'] += 1
    
    for flow in root.findall(".//xpdl:MessageFlow", ns):
        counts['Message Flows'] += 1
    for flow in root.findall(".//xpdl:SequenceFlow", ns):
        counts['Sequence Flows'] += 1
    for flow in root.findall(".//xpdl:DataAssociation", ns):
        counts['Associations'] += 1
        
    for pool in root.findall(".//xpdl:Pool", ns):
        counts['Pools'] += 1
    for lane in root.findall(".//xpdl:Lanes", ns):
        counts['Lanes'] += 1
    
    for subprocess in root.findall(".//xpdl:SubFlow", ns):
        counts['Subprocesses'] += 1
    
    counts['Tasks'] = counts['User Tasks'] + counts['Service Tasks'] + counts['Script Tasks'] + counts['Manual Tasks']
    counts['Events'] = counts['Start Events'] + counts['End Events'] + counts['Intermediate Events']
    counts['Gateways'] = counts['Gateways'] + counts['XOR Gateway'] + counts['AND Gateway'] + counts['OR Gateway']
    counts['Flows'] = counts['Message Flows'] + counts['Sequence Flows'] + counts['Associations']
    counts['Swimlanes'] = counts['Pools'] + counts['Lanes']
    
    categories = ['Tasks', 'Events', 'Gateways', 'Flows', 'Swimlanes', 'Subprocesses']
    subcategories = {
        'Tasks': ['User Tasks', 'Service Tasks', 'Script Tasks', 'Manual Tasks'],
        'Events': ['Start Events', 'End Events', 'Intermediate Events'],
        'Gateways': ['Gateways', 'XOR Gateway', 'AND Gateway', 'OR Gateway'],
        'Flows': ['Message Flows', 'Sequence Flows', 'Associations'],
        'Swimlanes': ['Pools', 'Lanes']
    }

# Print data in structured format
    for category in categories:
        print(f"{category}:")
        if category in subcategories:
            for subcategory in subcategories[category]:
                print(f"\t{subcategory}: {counts[subcategory]}")
        else:
            print(f"\t{category}: {counts[category]}")

def result(request):
    # return error if file is not present
    if not os.path.exists(xmlpath):
        return upload(request, error="File not found")

    myroot = ElTr.fromstring(readfile(request))
    
    # if (myroot.tag)
    
    lanelist = []
    processlist = []
    events = []
    tasks = []
    gateways = []
    flows = []
    datastores = []
    subprocesses = []

    # go into bpmn:definitions child 
    for child in myroot:
        # find number of bpmn:process child
        if child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}process":
            # save the all process child in a list
            processlist.append(child)

    for process in processlist:
        for child in process:
            if child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}laneSet":
                laneSet = child
                for lane in laneSet:
                    lanelist.append(lane)

            # events
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}startEvent":
                events.append(child)    
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}endEvent":
                events.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}intermediateCatchEvent":
                events.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}intermediateThrowEvent":
                events.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}boundaryEvent":
                events.append(child)

            # tasks
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}task":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}userTask":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}serviceTask":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}scriptTask":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}businessRuleTask":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}sendTask":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}receiveTask":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}manualTask":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}callActivity":
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}subProcess":
                subprocesses.append(child)
                # adding subprocesses to tasks list as well for calculating time 
                tasks.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}transaction":
                tasks.append(child)

            # gateways
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}exclusiveGateway":
                gateways.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}inclusiveGateway":
                gateways.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}parallelGateway":
                gateways.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}eventBasedGateway":
                gateways.append(child)
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}complexGateway":
                gateways.append(child)
            
            # flows
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}sequenceFlow":
                flows.append(child)

            # data stores
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}dataStoreReference":
                datastores.append(child)
            
            # subprocesses
            elif child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}subProcess":
                subprocesses.append(child)

    template_name = "index.html"

    processes_data = {}
    for process in processlist:
        for child in process:
            if process.attrib.get('name'):
                processes_data[process.attrib['name']] = 0

    # store name of the lanes, tasks, events and processes in a list
    lanes_data = {}

    for lane in lanelist:
        if lane.attrib.get('name'):
            lanes_data[lane.attrib['name']] = 0

    task_data = {}
    event_data = {}

    total_time = 0
    cycle_time = 0.0

    # go into extensionElements tag
    for task in tasks:            
        if task.attrib.get('name'):
            task_data[task.attrib['name']] = random.randint(5, 15)
            total_time += task_data[task.attrib['name']]
        for child in task:
            if child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}extensionElements":
                for child2 in child:
                    if child2.tag == "{http://camunda.org/schema/zeebe/1.0}properties":
                        current_time = 0.0
                        current_probability = 1.0
                        for child3 in child2:
                            if child3.tag == "{http://camunda.org/schema/zeebe/1.0}property":
                                # check if it have a Probability property
                                if child3.attrib['name'] == "Probability":
                                    current_probability = float(child3.attrib['value'])
                                # get the Time property 
                                if child3.attrib['name'] == "Time":
                                    print('asdsa', child3.attrib)
                                    task_data[task.attrib['name']] = child3.attrib['value']
                                    total_time += int(child3.attrib['value'])
                                    current_time = int(child3.attrib['value'])
                                    # check if the task is in a lane
                                    for lane in lanelist:
                                        for child4 in lane:
                                            if child4.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}flowNodeRef":
                                                if child4.text == task.attrib['id']:
                                                    lanes_data[lane.attrib['name']] += int(child3.attrib['value'])
                                    # check if the task is in a process
                                    for process in processlist:
                                        for child4 in process:
                                            if child4.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}task":
                                                if child4.attrib['id'] == task.attrib['id']:
                                                    processes_data[process.attrib['name']] += int(child3.attrib['value'])
                        cycle_time += current_time * current_probability

    print("Total time: " + str(total_time))

    for event in events:
        if event.attrib.get('name'):
            event_data[event.attrib['name']] = 0
            for child in event:
                if child.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}extensionElements":
                    for child2 in child:
                        if child2.tag == "{http://camunda.org/schema/zeebe/1.0}properties":
                            current_time = 0.0
                            current_probability = 1.0
                            for child3 in child2:
                                if child3.tag == "{http://camunda.org/schema/zeebe/1.0}property":
                                    # check if it have a Probability property
                                    if child3.attrib['name'] == "Probability":
                                        current_probability = float(child3.attrib['value'])
                                    # get the Time property 
                                    if child3.attrib['name'] == "Time":
                                        event_data[event.attrib['name']] = child3.attrib['value']
                                        current_time = int(child3.attrib['value'])
                                        total_time += int(child3.attrib['value'])
                                        # check if the task is in a lane
                                        for lane in lanelist:
                                            for child4 in lane:
                                                if child4.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}flowNodeRef":
                                                    if child4.text == event.attrib['id']:
                                                        lanes_data[lane.attrib['name']] += int(child3.attrib['value'])
                                        # check if the task is in a process
                                        for process in processlist:
                                            for child4 in process:
                                                if child4.tag == "{http://www.omg.org/spec/BPMN/20100524/MODEL}event":
                                                    if child4.attrib['id'] == event.attrib['id']:
                                                        processes_data[process.attrib['name']] += int(
                                                            child3.attrib['value'])
                            cycle_time += current_time * current_probability

    gateways_name = []

    for gateway in gateways:
        # add XOR, OR etc for the types of gatways
        # replace the type of gateway with XOR, OR etc
        g_type = gateway.tag.split("}")[1]
        
        if g_type == 'exclusiveGateway':
            g_type = '(XOR)'
        elif g_type == 'inclusiveGateway':
            g_type = '(OR)'
        elif g_type == 'parallelGateway':
            g_type = '(AND)'
        elif g_type == 'eventBasedGateway':
            g_type = '(Event Based)'
        
        gateways_name.append(gateway.attrib['name'] + ' ' + g_type)

    sum_events = 0
    sum_tasks = 0
    sum_lanes = 0
    sum_processes = 0
    
    for event in event_data:
        sum_events += int(event_data[event])

    for task in task_data:
        sum_tasks += int(task_data[task])

    for lane in lanes_data:
        sum_lanes += int(lanes_data[lane])

    for process in processes_data:
        sum_processes += int(processes_data[process])

    # if os.path.isfile("static/upload/bpmn.xml"):
    #     os.remove("static/upload/bpmn.xml")

    num_events = len(events)
    num_tasks = len(tasks)
    num_processes = len(processlist)

    # display the numbers of lanes, tasks, events and processes
    return render(request, template_name,
                  {'lanes': lanes_data, 'tasks': task_data, 'events': event_data, 'processes': processes_data,
                   'gateways': gateways_name, 'flows': flows, 'datastores': datastores, 'subprocesses': subprocesses, 
                   'num_events': num_events, 'num_tasks': num_tasks,    'num_processes': num_processes,
                   'sum_events': sum_events, 'sum_tasks': sum_tasks, 'sum_lanes': sum_lanes, 'sum_processes': sum_processes,
                   'total_time': total_time, 
                   'cycle_time': cycle_time})


# upload file
def upload(request, error=None):
    template_name = "upload.html"
    if request.method == "POST":
        form = forms.UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            fs = FileSystemStorage()
            # delete the old file if present
            if os.path.isfile("static/upload/bpmn.xml"):
                os.remove("static/upload/bpmn.xml")
            filename = fs.save("static/upload/bpmn.xml", request.FILES['file'])
            fs.url(filename)
            return redirect('result')
    else:
        form = forms.UploadFileForm()

    return render(request, template_name, {'form': form, 'error': error})
