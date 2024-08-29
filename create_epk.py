import json
import networkx as nx
import matplotlib.pyplot as plt
import pydot
from networkx.drawing.nx_pydot import graphviz_layout
import ollama
import re
import time
from networkx.drawing.nx_pydot import to_pydot

'''
Parameters that can be set from the user
'''
# Amount of EPK's which should be generated in the run
amount_of_epk = int(input("Wie viele EPK's sollen generiert werden? "))

# User can choose which model to use
# Please run in your terminal 'ollama list' before to make sure you have the model you want to use
llm_model = input("Zur Auswahl stehen: phi3, phi3more qwen, phi, mistral, llama3. Welches LLM Model soll verwendet werden? ")

# Theme of the EPK's can be set here. For the comparability it is always the same theme here
theme = "procurement process of an international company" # input("Please insert a theme for the EPK: ")


'''
@call_LLM is a function to send the prompt to the ollama LLM, which the user has chosen before
    input:
        LLM model - Specified by the user.
        prompt - Generated automatically via templates.
    output:
        Output - Response of the LLM. The response comes in a JSON format. It gets transformed so that only the content 
                 which the LLM has generated in this run is used.
'''
def call_LLM(LLM_model,prompt):
    language_model = LLM_model
    formatted_template = prompt
    Output = ollama.chat(model=language_model,messages=[{'role': 'user','content': formatted_template,},], keep_alive=10.0)
    Output = Output['message']['content']
    # Replace ':' to '-' -> Neccessary to write it into the graph
    Output = re.sub(r':', '-', Output)
    return Output

'''
@subprocess_dissambly subprocesses are disassembled into a format which makes it possible to use them for labeling
    input:
        Output_subprocess - Response from the function @call_LLM .
        attr_type - Type of the gate node. Seeable in the JSON under: "type". Can have the following values: ANDGate, ORGate, XORGate.
        attr_status - Status of gate node. Seeable in the JSON under: "status". Can have the following values: opening, closing.
        attr_pattern - Pattern type of the gate node. Seeable in the JSON under: "patternType". Can have the following values: AND, OR, XOR.
    output:
        matching of the elements to the edges of the subprocesses in the EPK
'''
def subprocess_dissambly(Output_subprocess, attr_type, attr_status, attr_pattern):
                # Regular expression to get every single subprocess in the response. They get separated by " Subprocess 'number' - "
                pattern = re.compile(r"Subprocess \d+ - (.*?)(?=\nSubprocess \d+ -|\Z)", re.DOTALL)
                # Disassemble all subprocesses into a list
                subprocess_list_dirty = pattern.findall(Output_subprocess)
                subprocess_list = []
                for subprocess in subprocess_list_dirty:
                    subprocess = re.sub(r'\n', '', subprocess)
                    subprocess = re.sub(r'-', '', subprocess)
                    subprocess = re.sub(r'"', '', subprocess)
                    subprocess = re.sub(r"'", "'", subprocess)
                    subprocess = re.sub(r'_', ' ', subprocess)
                    subprocess_list.append(subprocess)
                # Catch all outgoing edges from the last gate with the status "opening"
                gate_nodes = [node for node in G.nodes(data=True) if node[1]['type'] == attr_type and node[1].get('status') == attr_status and node[1].get('patternType') == attr_pattern]
                for node, attrs in gate_nodes:
                    outgoing_edges = list(G.out_edges(node, keys=True))
                    for i, (u, v, key) in enumerate(outgoing_edges):
                        if i < len(subprocess_list):
                            # Attach the label from subprocess_list to the outgoing chain. The order is chosen after Round Robin
                            G[u][v][key]['label'] = subprocess_list[i]
                        else:
                            break


'''
@subprocess_LOOP_dissambly Loop Subprocesses are disassembled into a format which makes it possible to use them for labeling. 
    Function is not used at the moment.
    input:
        Output_subprocess - Response from the function @call_LLM
        attr_type - Type of the gate node. Seeable in the JSON under: "type". Can have the following values: ANDGate, ORGate, XORGate.
        attr_status - Status of gate node. Seeable in the JSON under: "status". Can have the following values: opening, closing.
        attr_pattern - Pattern type of the gate node. Seeable in the JSON under: "patternType". Can have the following values: LOOP.
    output:
        matching of the elements to the edges of the subprocesses in the EPK.
'''
def subprocess_LOOP_dissambly(Output_subprocess, attr_type, attr_status, attr_pattern):
    # # Regular expression to get every single subprocess in the response. They get separated by " Subprocess 'something' - "
    pattern = re.compile(r"Subprocess (LOOP|\d+)  (.*?)(?=\nSubprocess (?:LOOP|\d+) |\Z)", re.DOTALL)
    # Zerlege alle Subprozesse in eine Liste
    subprocess_list_dirty = pattern.findall(Output_subprocess)
    subprocess_list = []
    for sp_type, subprocess in subprocess_list_dirty:
        subprocess = re.sub(r'\n', '', subprocess).strip()
        if sp_type == "LOOP":
            subprocess_list.append(f"LOOP - {subprocess}")
        else:
            subprocess_list.append(subprocess)
    # Zugreifen auf ausgehende Kanten von ANDGates mit dem Status "opening"
    gate_nodes = [node for node in G.nodes(data=True) if node[1]['type'] == attr_type and node[1].get('status') == attr_status and node[1].get('patternType') == attr_pattern]
    for node, attrs in gate_nodes:
        outgoing_edges = list(G.out_edges(node, keys=True))
        for i, (u, v, key) in enumerate(outgoing_edges):
            if i < len(subprocess_list):
                # Attach the label from subprocess_list to the outgoing chain. The order is chosen after Round Robin
                # could be improved in the future so that the subprocess Loop actually matches its counterpart in the graph
                G[u][v][key]['label'] = subprocess_list[i]
            else:
                break

'''@incoming_labels reads the label of the incomming edge and matches it as a preparation to 
    create the template of the current event-function-event prompt.
    It is the counterpart to @subprocess_dissambly which writes the label to the incomming edge
    input:
        node_ids - Id of the current node.
    output: 
        Output_subgraph - returns the label of the current subprocess.
'''
def incoming_labels(node_ids):
    if node_ids:
        first_node_id = node_ids[0]
        incoming_edges = G.in_edges(first_node_id, keys=True)
        incoming_label = [G[u][v][key]['label'] for u, v, key in incoming_edges if 'label' in G[u][v][key]]
        # If a label for @Output_subgraph exists it gets used otherwise it is set to the label of the StartEPC
        # to keep the templates in order even if there was an error with the matching of the subprocesses before
        if incoming_label:
            Output_subgraph = incoming_label[0] 
        else:
            Output_subgraph = Output_StartEPC
    else:
        # if no node exists it should return this message.
        Output_subgraph = 'No node in the subgraph'
    return Output_subgraph

'''
@label_EFE_attachment attaches the Event/Function to the comming node. 
Could be optimized by a more clear differentiation between Event and Function.
    input:
        Output_EFE - Output of the function @call_LLM converted into a list.
    output:
        Nodes of the EFE chain with setted labels
'''
def label_EFE_attachment(Output_EFE): 
                labels = [line.strip() for line in Output_EFE.strip().split('\n') if line.strip()]
                for node_id, label in zip(node_ids, labels):
                    G.nodes[node_id]['label'] = label

'''
@clean_output clean the output of the LLM from errors. 
The intention is to apply regex functions so that the output of the LLM gets formatted in the way we need for the visualisation
Function is not used yet given the fact that the parameters in the modelfiles are fine tuned. The function @clean_output is a backup
plan when the fine tuning is not working. Might be applied in the future.
    input:
        output - Response of the function @call_LLM.
    Output:
        output - Response without any signs which are not wanted in the label.
'''
def clean_output(output):
# Entferne die spezifischen Zeichen
    output = re.sub(r'[\n\-"]', '', output)
    output = re.sub(r"'", '', output)
    output = re.sub(r'_', ' ', output)

    # Füge Leerzeichen zwischen Wörtern ein
    output = re.sub(r'([a-z])([A-Z])', r'\1 \2', output)

    return output
'''
@create_function_event_sequence function is creating the function-event-function sequence which is used by the templates.
It reads the length of the sequences and determines in which order the element event-function are in the chain.
The returned values get used in the templates which are send to the LLM.
    input:
        subgraph - The current segment in the graph.
        graph - The whole input JSON as graph in the style of the networkX library.
    output:
        join(sequence) - Sequence of the Event-Function-Event chain. It is a string value which looks like this: "Event Function Event".
        len(sequence) - Length of the Event-Function-Event chain. Is the number of all elements in the chain.
'''
def create_function_event_sequence(subgraph, graph):
    sequence = []
    # loop to get every single node from the current subgraph
    for node in subgraph:
        node_type = graph.nodes[node['segment']]['type']
        sequence.append(node_type)
    return ', '.join(sequence), len(sequence)

'''
@set_gate_label set the label of the gates. Default string values depending if it is an AND/OR/XOR/LOOP and if it is opening/closing
    input:
        node_attrs - All attributes of one specific node.
    output: 
        correctly matched label to the specific node
'''
def set_gate_label(node_attrs):
    if node_attrs['type'] == 'ANDGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'AND':
        # Set the label for the ANDGate subprocesses in the graph
        node_attrs['label'] = "AND Gate Opening"
    elif node_attrs['type'] == 'ORGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'OR':
        # Set the label for the ORGate subprocesses in the graph
        node_attrs['label'] = "OR Gate Opening"
    elif node_attrs['type'] == 'XORGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'XOR':
        # Set the label for the XORGate subprocesses in the graph
        node_attrs['label'] = "XOR Gate Opening"
    elif node_attrs['type'] == 'ANDGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'LOOP':
        # Set the label for the ANDGate subprocesses in the graph
        node_attrs['label'] = "AND Gate LOOP"
    elif node_attrs['type'] == 'ORGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'LOOP':
        # Set the label for the ORGate subprocesses in the graph
        node_attrs['label'] = "OR Gate LOOP"
    elif node_attrs['type'] == 'XORGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'LOOP':
        # Set the label for the XORGate subprocesses in the graph
        node_attrs['label'] = "XOR Gate LOOP"

'''
@calculate_label_completeness function which generates a metric to calculate if every node of the graph has a label.
The function does only check the existence of the label and not if the label has the right format or content.
    input:
        graph - The whole JSON as graph in the style of the networkX library which is generated after the LLM run.
    output:
        completeness_percentage: Number from 0.00% - 100.00%% which tell how many labels for the graph are setted.
'''
def calculate_label_completeness(graph):
    total_with_label = 0
    total_with_label_value = 0
    
    # Check the nodes
    for node, data in graph.nodes(data=True):
        if 'label' in data:
            total_with_label += 1
            if data['label']:
                total_with_label_value += 1
                
    # Check the edges
    for u, v, key, data in graph.edges(keys=True, data=True):
        if 'label' in data:
            total_with_label += 1
            if data['label']:
                total_with_label_value += 1
                
    completeness_percentage = (total_with_label_value / total_with_label) * 100 if total_with_label > 0 else 0
    
    return completeness_percentage

'''
for loop to run the process of labeling a graph as often as the user wants it
'''
for iteration in range(amount_of_epk):
    # record the starting time
    start_time = time.time()
   
    '''
    Various templates for all possible case. 
        - The start and the end event have their own templates
        - The AND/OR/XOR/LOOP gates have their own templates
        - All Event-Function-Event chains have their own templates
        - All gates with nested loops have their own templates
    EFE - Event, Function, Event cahin
    '''
    templates = {
        "StartEPC" : "In the context of an event driven process chain about {Template_Theme}, provide a starting event. The starting event should be made up of concrete instances of the following part-of-speech tags: 'NOUN AUX VERB NOUN', and provide a sentence in passive voice, e.g. 'person has received information' or 'text is displayed'. Prefix your answer with the keyword 'StartEvent - '. In the following we will go through all {amount_nodes} nodes of the process description. Take care of the atomicity of elements. Do not give further explanations on the output. Use maximum 80 symbols.",
        "EndEPC" : "In an event-driven process chain about a {Template_Theme} starting with {Output_StartEPC}, provide an end event in the style of the part-of-speech tags 'NOUN AUX VERB NOUN' in passive voice. Example: 'contract has been signed'. Prefix with 'EndEvent - '. Ensure atomicity. The event must be unique and not previously mentioned. The words should be separated by whitespaces.  Do NOT mention NOUN AUX VERB NOUN. Max 80 symbols. No explanations.",
        "StartEFE" : "In the context of an event driven process chain about  {Template_Theme}, with the starting event {Output_StartEPC}, The process is made up of {amount_elements} elements: {elements_string}. Provide descriptions for the {amount_elements} given process elements in this order: {elements_string}. ‘Events‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice and ‘Functions‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answers for each process element with their respective type, e.g. ‘Function - ‘ OR ‘Event - ‘ and separate them with the newline character ‘\n‘. Do NOT generate more than the requested {amount_elements} process elements:  '{Event_function_chain}'. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones.The words should be separated by whitespaces. Use maximum 80 symbols for one element.",

        "ANDStart" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC}, provide names of {amount_subgraphs} branches of parallel subprocesses. Prefix each with 'Subprocess %Number% - '. Each name must be unique and not previously mentioned. Max 80 symbols each. No explanations.",
        "ANDStartLOOP": "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC}, provide names of {amount_subgraphs} branches of parallel subprocesses. Prefix each with 'Subprocess %Number% - '. One subprocess shall be in a loop which has to be closed in the future. Mark it with ‘Subprocess LOOP - ‘. Do NOT mention loop in any form otherwise. Each name must be unique and not previously mentioned. Max 80 symbols each. No explanations.",
        "ANDSubEFE" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} parallel subprocesses, describe the events and functions of the subprocess {Output_subgraph}. The process consists of exactly {amount_elements_subprocesses} elements in this order: '{Event_function_chain}'. Provide descriptions for the {amount_elements_subprocesses} given process elements in this order: {elements_string}. ‘Events‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice and ‘‘Functions‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answers for each process element with their respective type, e.g. ‘Function - ‘ OR ‘Event - ‘ and separate them with the newline character ‘\n‘. Do NOT generate more than the requested {amount_elements_subprocesses} process elements:  ‘{Event_function_chain}‘ Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 80 symbols for one element.",
        "ANDSubOneEvent" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} parallel subprocesses, describe the one event of the subprocess {Output_subgraph}. The process consists of exactly one element. ‘Event‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice. Prefix your answer with ‘Event - ‘ . Do NOT generate more than the requested ONE event. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 20 symbols.",
        "ANDSubOneFunction" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} parallel subprocesses, describe the one function of the subprocess {Output_subgraph}. The process consists of exactly one element. ‘Function‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answer with ‘Function - ‘. Do NOT generate more than the requested ONE function. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 20 symbols.",

        "XORStart" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} provide names of {amount_subgraphs} branches of mutually exclusive subprocesses. Prefix each with 'Subprocess %Number% - '. Each name must be unique and not previously mentioned. Max 80 symbols each. No explanations.",
        "XORStartLOOP": "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} provide names of {amount_subgraphs} branches of mutually exclusive subprocesses. Prefix each with 'Subprocess %Number% - '. One subprocess shall be in a loop which has to be closed in the future. Mark it with ‘Subprocess LOOP - ‘. Do NOT mention loop in any form otherwise. Each name must be unique and not previously mentioned. Max 80 symbols each. No explanations.",
        "XORSubEFE" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} mutually exclusive parallel subprocesses, describe the events and functions of the subprocess {Output_subgraph}. The process consists of exactly {amount_elements_subprocesses} elements in this order: '{Event_function_chain}'. Provide descriptions for the {amount_elements_subprocesses} given process elements in this order: {elements_string}. ‘Events‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice and ‘‘Functions‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answers for each process element with their respective type, e.g. ‘Function - ‘ OR ‘Event - ‘ and separate them with the newline character ‘\n‘. Do NOT generate more than the requested {amount_elements_subprocesses} process elements:  ‘{Event_function_chain}‘ Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 80 symbols for one element.",
        "XORSubOneEvent" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} mutually exclusive parallel subprocesses, describe the one event of the subprocess {Output_subgraph}. The process consists of exactly one element. ‘Event‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice. Prefix your answer with ‘Event - ‘ . Do NOT generate more than the requested ONE event. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 20 symbols.",
        "XORSubOneFunction" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} mutually exclusive parallel subprocesses, describe the one function of the subprocess {Output_subgraph}. The process consists of exactly one element. ‘Function‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answer with ‘Function - ‘. Do NOT generate more than the requested ONE function. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 20 symbols.",

        "ORStart" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} provide the names of {amount_subgraphs} branches of alternative subprocesses. Prefix each with 'Subprocess %Number% - '. Each name must be unique and not previously mentioned. Max 80 symbols each. No explanations.",
        "ORStartLOOP": "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} provide the names of {amount_subgraphs} branches of alternative subprocesses. Prefix each with 'Subprocess %Number% - '. One subprocess shall be in a loop which has to be closed in the future. Mark it with ‘Subprocess LOOP - ‘. Do NOT mention loop in any form otherwise. Each name must be unique and not previously mentioned. Max 80 symbols each. No explanations.",
        "ORSubEFE" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} alternative parallel subprocesses, describe the events and functions of the subprocess {Output_subgraph}. The process consists of exactly {amount_elements_subprocesses} elements in this order: '{Event_function_chain}'. Provide descriptions for the {amount_elements_subprocesses} given process elements in this order: {elements_string}. ‘Events‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice and ‘‘Functions‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answers for each process element with their respective type, e.g. ‘Function - ‘ OR ‘Event - ‘ and separate them with the newline character ‘\n‘. Do NOT generate more than the requested {amount_elements_subprocesses} process elements:  ‘{Event_function_chain}‘ Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 80 symbols for one element.",
        "ORSubOneEvent" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} alternative parallel subprocesses, describe the one event of the subprocess {Output_subgraph}. The process consists of exactly one element. ‘Event‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice. Prefix your answer with ‘Event - ‘ . Do NOT generate more than the requested ONE event. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 20 symbols.",
        "ORSubOneFunction" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} alternative parallel subprocesses, describe the one function of the subprocess {Output_subgraph}. The process consists of exactly one element. ‘Function‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answer with ‘Function - ‘. Do NOT generate more than the requested ONE function. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 20 symbols.",

        "LOOPSubEFE":"In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} subprocesses, describe the events and functions of the potentially repeating subprocess {Output_subgraph}. The process consists of exactly {amount_elements_subprocesses} elements in this order: '{Event_function_chain}'. Provide descriptions for the {amount_elements_subprocesses} given process elements in this order: {elements_string}. ‘Events‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice and ‘‘Functions‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answers for each process element with their respective type, e.g. ‘Function - ‘ OR ‘Event - ‘ and separate them with the newline character ‘\n‘. Do NOT generate more than the requested {amount_elements_subprocesses} process elements:  ‘{Event_function_chain}‘ Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 80 symbols for one element.",
        "LOOPSubOneEvent" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} subprocesses, describe the one event of the potentially repeating subprocess {Output_subgraph}. The process consists of exactly one element. ‘Event‘ is made up of concrete instances of the following part of speech tags ‘NOUN AUX VERB NOUN‘ in passive voice. Prefix your answer with ‘Event - ‘ . Do NOT generate more than the requested ONE event. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 20 symbols.",
        "LOOPSubOneFunction" : "In an event-driven process chain about a {Template_Theme}, starting with {Output_StartEPC} and involving {amount_subgraphs} subprocesses, describe the one function of the potentially repeating subprocess {Output_subgraph}. The process consists of exactly one element. ‘Function‘ is made up of concrete instances of the following part of speech tags ‘NOUN VERB NOUN‘ in active voice. Prefix your answer with ‘Function - ‘. Do NOT generate more than the requested ONE function. Do not give further explanations on the output. The elements CANNOT be one of the already mentioned ones. The words should be separated by whitespaces. Use maximum 20 symbols."        
    }
    '''
    Initialisation of all placeholders
    '''
    placeholder = {
        "Template_Theme" : "Should be defined by user",
        "Output_StartEPC" : "Result of the first template from LLM",
        "Event_function_chain":"Contains a chain of Event, Function, Event in all imaginable ways",
        "amount_elements_subprocesses" : "Amount of elements in EFE",
        "amount_subgraphs" : "Amount subgraphs",
        "Output_subgraph" : "Name of the subgraph"
    }


    # Path to the JSON file gets specified
    file = 'graphs/epc_11360__0.5169854086147916.json'

    # Creation of the NetworkX graph
    G = nx.MultiDiGraph()
    segments = {}

    with open(file, "r") as json_file:
        data = json.load(json_file)
        # Filter the data from the JSON into EPC (Event driven process chain)
        epc_data = data["epc"]
        segment_data = data["segmentedGraph"]

    # Extract Nodes and Edges
    nodes = data['epc']['nodes']
    edges = data['epc']['edges']
    segmented_graph = data['segmentedGraph']

    # Add nodes to the graph
    for node in nodes:
        G.add_node(node['key'], **node['attributes'])

    # Add edges to the graph
    for edge in edges:
        G.add_edge(edge['source'], edge['target'], key=edge['key'], **edge['attributes'])


    # Set a label for every node. Doing that ensures that a node is just empty in case there is an error with the LLM
    for node in G.nodes:
        # decomment the line when you want to set the number of the node as label
        #label = f"{node}:                                      ."
        label = ".                                             ."
        G.nodes[node]['label'] = label


    # Templates to save later in output files
    template_assignments = []
    output_list = []

    # Get the amount of all nodes
    amount_nodes = str(len(G.nodes()))

    # Set the topic of the EPC
    theme = "procurement process of an international company" 
    # theme = input("Please insert a theme for the EPK: ")

    # Iterate through the semgents of the graph
    for segment in data['segmentedGraph']:
        if segment['type'] == 'node':  
            node_type = G.nodes[segment['segment']]['type']
            node_id = segment['segment']
            node_attrs = G.nodes[node_id]
            node_pattern_type = node_attrs.get('patternType', '')
            node_status = node_attrs.get('status', '')

            if node_pattern_type == 'StartEPC':
                formatted_template_start_EPC = templates['StartEPC'].replace('{Template_Theme}', theme).replace('{amount_nodes}', amount_nodes)
                template_assignments.append((node_id, formatted_template_start_EPC))

                # Send the template to the LLM and get the result
                Output_StartEPC = call_LLM(llm_model,formatted_template_start_EPC)

                output_list.append((node_id,Output_StartEPC))

                # Format the startEPC into the correct format
                Output_StartEPC = re.sub(r'-', 'TEMPDASH', Output_StartEPC, count=1)
                Output_StartEPC = re.sub(r'[^\w\sTEMPDASH]', '', Output_StartEPC)
                Output_StartEPC = re.sub(r'TEMPDASH', '-', Output_StartEPC)

                # Set the label for the startEPC in the graph
                node_attrs['label'] = f"{Output_StartEPC}"
                start_EPC = f"User: {formatted_template_start_EPC} \n Phi3: {Output_StartEPC} \n"


            # Count the subprocesses of the node
            amount_subgraphs = G.out_degree(node_id)

            if node_pattern_type == 'EndEPC':
                formatted_template = templates['EndEPC'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{amount_subgraphs}', str(amount_subgraphs))
                template_assignments.append((node_id, formatted_template))
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send the template to the LLM and get the result
                Output_EndEPC = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_EndEPC))

                # Set the label for the endEPC in the graph
                node_attrs['label'] = f"{Output_EndEPC}"

            elif node_attrs['type'] == 'ANDGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'AND':
                formatted_template = templates['ANDStart'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{amount_subgraphs}', str(amount_subgraphs))
                template_assignments.append((node_id, formatted_template))
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send the template to the LLM and get the result
                Output_ANDGate = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_ANDGate))

                # Set the label for the ANDGate subprocesses in the graph
                node_attrs['label'] = f"{Output_ANDGate}"

                # Separate the output into subprocesses of the outgoing edges
                subprocess_dissambly(Output_ANDGate, 'ANDGate', 'opening', 'AND')



            elif node_attrs['type'] == 'ANDGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'LOOP':
                formatted_template = templates['ANDStartLOOP'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{amount_subgraphs}', str(amount_subgraphs))
                template_assignments.append((node_id, formatted_template))
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send the template to the LLM and get the result
                Output_ANDLOOP = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_ANDLOOP))

                # Set the label for the ANDLOOP subprocesses in the graph
                node_attrs['label'] = f"{Output_ANDLOOP}"

                # Separate the output into subprocesses of the outgoing edges
                #subprocess_LOOP_dissambly(Output_ANDLOOP, 'ANDGate', 'opening', 'LOOP') # New function for the typ LOOP as a trial
                subprocess_dissambly(Output_ANDLOOP, 'ANDGate', 'opening', 'LOOP')

            elif node_attrs['type'] == 'ANDGate' and node_attrs.get('status') == 'closing' and node_attrs.get('patternType') == 'AND':
                node_attrs['label'] = "AND Gate closing"

            elif node_attrs['type'] == 'ANDGate' and node_attrs.get('status') == 'closing' and node_attrs.get('patternType') == 'LOOP':
                node_attrs['label'] = "AND LOOP closing"

            elif node_attrs['type'] == 'ORGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'OR':
                formatted_template = templates['ORStart'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{amount_subgraphs}', str(amount_subgraphs))
                template_assignments.append((node_id, formatted_template))
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send the template to the LLM and get the result
                Output_ORGate = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_ORGate))

                # Set the label for the ORGate subprocesses in the graph
                node_attrs['label'] = f"{Output_ORGate}"

                # Separate the output into subprocesses of the outgoing edges
                subprocess_dissambly(Output_ORGate, 'ORGate', 'opening', 'OR')

            elif node_attrs['type'] == 'ORGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'LOOP':
                formatted_template = templates['ORStartLOOP'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{amount_subgraphs}', str(amount_subgraphs))
                template_assignments.append((node_id, formatted_template))
                node_attrs['label'] = "OR LOOP opening"
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send the template to the LLM and get the result
                Output_ORLOOP = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_ORLOOP))

                # Set the label for the ORLOOP subprocesses in the graph
                node_attrs['label'] = f"{Output_ORLOOP}"

                # Separate the output into subprocesses of the outgoing edges
                #subprocess_LOOP_dissambly(Output_ORLOOP, 'ORGate', 'opening', 'LOOP')
                subprocess_dissambly(Output_ORLOOP, 'ORGate', 'opening', 'LOOP')

            elif node_attrs['type'] == 'ORGate' and node_attrs.get('status') == 'closing' and node_attrs.get('patternType') == 'OR':
                node_attrs['label'] = "OR Gate closing"

            elif node_attrs['type'] == 'ORGate' and node_attrs.get('status') == 'closing' and node_attrs.get('patternType') == 'LOOP':
                node_attrs['label'] = "OR LOOP closing"

            elif node_attrs['type'] == 'XORGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'XOR':
                formatted_template = templates['XORStart'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{amount_subgraphs}', str(amount_subgraphs))
                template_assignments.append((node_id, formatted_template))
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send the template to the LLM and get the result
                Output_XORGate = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_XORGate))

                # Set the label for the XORGatesubprocesses in the graph
                node_attrs['label'] = f"{Output_XORGate}"

                # Separate the output into subprocesses of the outgoing edges
                subprocess_dissambly(Output_XORGate, 'XORGate', 'opening', 'XOR')

            elif node_attrs['type'] == 'XORGate' and node_attrs.get('status') == 'opening' and node_attrs.get('patternType') == 'LOOP':
                formatted_template = templates['XORStartLOOP'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{amount_subgraphs}', str(amount_subgraphs))
                template_assignments.append((node_id, formatted_template))
                node_attrs['label'] = "XOR LOOP opening"
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send the template to the LLM and get the result
                Output_XORLOOP = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_XORLOOP))

                # Set the label for the ANDLOOP subprocesses in the graph
                node_attrs['label'] = f"{Output_XORLOOP}"

                # Separate the output into subprocesses of the outgoing edges
                #subprocess_LOOP_dissambly(Output_XORLOOP, 'XORGate', 'opening', 'LOOP')
                subprocess_dissambly(Output_XORLOOP, 'XORGate', 'opening', 'LOOP')

            elif node_attrs['type'] == 'XORGate' and node_attrs.get('status') == 'closing' and node_attrs.get('patternType') == 'LOOP':
                node_attrs['label'] = "XOR LOOP closing"
            elif node_attrs['type'] == 'XORGate' and node_attrs.get('status') == 'closing' and node_attrs.get('patternType') == 'XOR':
                node_attrs['label'] = "XOR Gate closing"

        elif segment['type'] == 'subGraph':  
            # Get the node IDs of subgraphs for an analysis of the graph
            node_ids = [node['segment'] for node in segment['segment']]
            pattern_types = {G.nodes[node_id]['patternType'] for node_id in node_ids}
            pattern_types_count = {}

        # Counts how often a PatternType exists in a segment. Based on that it gets decided which Type gets mapped to the subprocess
        # Possible values are: XOR, OR, AND, LOOP
            for node_id in node_ids:
                pattern_type = G.nodes[node_id]['patternType']
                if pattern_type in pattern_types_count:
                    pattern_types_count[pattern_type] += 1
                else:
                    pattern_types_count[pattern_type] = 1

            pattern_types_str = str(max(pattern_types_count, key=pattern_types_count.get))

            # Determine the Event-Function Chain
            subgraph_nodes = segment['segment']
            sequence, sequence_length = create_function_event_sequence(subgraph_nodes, G)

            # Set a value in case no value gets received from the LLM
            Output_subgraph = "???????????????????????????????"


            if pattern_types_str == 'AND':
                # The edges of the first node in the subgraph get reviewed and used as label
                Output_subgraph = incoming_labels(node_ids)

                # If condition to give another template when there is only one 'Event' or 'Function' in the template
                if sequence_length == 1 and sequence == 'Event':
                    formatted_template = templates['ANDSubOneEvent'].replace('{Template_Theme}', theme).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                elif sequence_length == 1 and sequence == 'Function':
                    formatted_template = templates['ANDSubOneFunction'].replace('{Template_Theme}', theme).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                else:
                    formatted_template = templates['ANDSubEFE'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{Event_function_chain}', sequence).replace('{amount_elements_subprocesses}', str(sequence_length)).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                template_assignments.append(("Subgraph Nodes: " + ', '.join(node_ids), formatted_template))
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send the template to the LLM
                Output_ANDEFE = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_ANDEFE))

                # Extract labels from the output and store them in a list
                label_EFE_attachment(Output_ANDEFE)



            if pattern_types_str == 'XOR':

                Output_subgraph = incoming_labels(node_ids)

                # If condition to give another template when there is only one 'Event' or 'Function' in the template
                if sequence_length == 1 and sequence == 'Event':
                    formatted_template = templates['XORSubOneEvent'].replace('{Template_Theme}', theme).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                elif sequence_length == 1 and sequence == 'Function':
                    formatted_template = templates['XORSubOneFunction'].replace('{Template_Theme}', theme).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                else:
                    formatted_template = templates['XORSubEFE'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{Event_function_chain}', sequence).replace('{amount_elements_subprocesses}', str(sequence_length)).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
    
                template_assignments.append(("Subgraph Nodes: " + ', '.join(node_ids), formatted_template))
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send Template to LLM
                Output_XOREFE = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_XOREFE))

                # Extract labels from the output and store them in a list
                label_EFE_attachment(Output_XOREFE)


            if pattern_types_str == 'OR':

                Output_subgraph = incoming_labels(node_ids)

                # If condition to give another template when there is only one 'Event' or 'Function' in the template
                if sequence_length == 1 and sequence == 'Event':
                    formatted_template = templates['ORSubOneEvent'].replace('{Template_Theme}', theme).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                elif sequence_length == 1 and sequence == 'Function':
                    formatted_template = templates['ORSubOneFunction'].replace('{Template_Theme}', theme).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                else:
                    formatted_template = templates['ORSubEFE'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{Event_function_chain}', sequence).replace('{amount_elements_subprocesses}', str(sequence_length)).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                template_assignments.append(("Subgraph Nodes: " + ', '.join(node_ids), formatted_template))
                formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send Template to LLM
                Output_OREFE = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_OREFE))

                # Extract labels from the output and store them in a list
                label_EFE_attachment(Output_OREFE)

            if pattern_types_str == 'LOOP':

                Output_subgraph = incoming_labels(node_ids)

                # If condition to give another template when there is only one 'Event' or 'Function' in the template
                if sequence_length == 1 and sequence == 'Event':
                    formatted_template = templates['LOOPSubOneEvent'].replace('{Template_Theme}', theme).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                elif sequence_length == 1 and sequence == 'Function':
                    formatted_template = templates['LOOPSubOneFunction'].replace('{Template_Theme}', theme).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                else:
                    formatted_template = templates['LOOPSubEFE'].replace('{Template_Theme}', theme).replace('{Output_StartEPC}', Output_StartEPC).replace('{Event_function_chain}', sequence).replace('{amount_elements_subprocesses}', str(sequence_length)).replace('{amount_subgraphs}', str(amount_subgraphs)).replace('{Output_subgraph}', Output_subgraph)
                template_assignments.append(("Subgraph Nodes: " + ', '.join(node_ids), formatted_template))
                #formatted_template = f"{start_EPC} User: {formatted_template}"

                # Send Template to LLM
                Output_LOOPEFE = call_LLM(llm_model,formatted_template)

                output_list.append((node_id,Output_LOOPEFE))

                # Extract labels from the output and store them in a list
                label_EFE_attachment(Output_LOOPEFE)

            # Determine Subgraph Funktion-Event Chain
            sequence = create_function_event_sequence(segment['segment'], G)


    """
    The following for-loop is there to label the XOR/OR/AND Gates as Opening gates and delete the Subprocess in the node of it. 
    The code may seem redundant and slow, but it works.
    """

    # Iterate through the segments of the graph
    for segment in data['segmentedGraph']:
        if segment['type'] == 'node': 
            node_type = G.nodes[segment['segment']]['type']
            node_id = segment['segment']
            node_attrs = G.nodes[node_id]
            node_pattern_type = node_attrs.get('patternType', '')
            node_status = node_attrs.get('status', '')

            # Call the function to set the label of the Gate
            set_gate_label(node_attrs)

    completeness_percentage = calculate_label_completeness(G)
    completeness = str(f'Prozentwert für die Vollständigkeit der gesetzten Label: {completeness_percentage:.2f}% \n')
    print(completeness)

    # Save Templates for the nodes in ordered_templates.txt
    with open(f'{llm_model}/ordered_templates_{iteration}.txt', "w") as text_file:
        for assignment in template_assignments:
            text_file.write(f'{assignment[0]}: {assignment[1]}\n')

    # Save outputs of the Templates as well in .txt
    with open(f'{llm_model}/ordered_output_llm_{iteration}.txt', "w") as text_file:
        for order in output_list:
            text_file.write(f'{order[0]}: {order[1]}\n')

    # Safe the result of the labeling in a new JSON-File
    # Convert the graph into a JSON-compatible format
    data = nx.readwrite.json_graph.node_link_data(G)
    
    # Write the JSON-Data into a new file
    output_file = f'{llm_model}/modified_graph_{iteration}.json'
    with open(output_file, "w") as json_out:
        json.dump(data, json_out, indent=4)

    
    pydot_graph = to_pydot(G)

    # Adapt the shape of a node whether it is a function or an event
    for node in pydot_graph.get_nodes():
        attrs = node.get_attributes()
        if 'type' in attrs and attrs['type'] == 'Function':
            node.set_shape('rectangle')
        elif 'type' in attrs and attrs['type'] == 'Event':
            node.set_shape('hexagon')

    # Export the PyDot graph to a JPEG file
    jpeg_path = str(f'{llm_model}/visualization_{iteration}.jpeg')
    pydot_graph.write_png(jpeg_path)

    # Calculate the time needed to create the epc
    elapsed_time = time.time() - start_time

    print(f"Die Ausführungsdauer für EPK Nummer {iteration} betrug {elapsed_time} Sekunden.")



