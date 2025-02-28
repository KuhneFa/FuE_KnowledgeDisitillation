import nltk
import json
from nltk.tokenize import word_tokenize
from nltk import pos_tag
import nltk
import ssl
import matplotlib.pyplot as plt
from collections import Counter

#nltk.download('punkt')
#nltk.download('punkt_tab')
#nltk.download('averaged_perceptron_tagger')
#nltk.download('averaged_perceptron_tagger_eng')

import re

import matplotlib
matplotlib.use('TkAgg')  # Alternativ: Qt5Agg


# Listen um die Verteilung der POS-Tags in den Listen zu zählen
NOUN_NOUN_FUNCTION_list = []
NOUN_VERB_FUNCTION_list = []
NOUN_VERB_NOUN_FUNCTION_list = []
NOUN_NOUN_CC_VERB_FUNCTION_list = []

NOUN_AUX_VERB_NOUN_EVENT_list = []
NOUN_VERB_VERB_EVENT_list = []
NOUN_NOUN_VERB_EVENT_list = []
NOUN_AUX_VERB_EVENT_list = []
NOUN_VERB_EVENT_list=[]
NOUN_AUX_EVENT_list = []
ADJ_NOUN_VERB_EVENT_list=[]



# Regex zum Entfernen von Satzzeichen und Prozentwerten
def remove_punctuation_and_percent(text):
    # Satzzeichen und Prozentzeichen entfernen
    cleaned_text = re.sub(r'[.,;!?%]+', '', text)
    # Zusätzliche Leerzeichen durch die Entfernung von Zeichen reduzieren
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def check_function_pattern(graph):
    """
    Zählt die Knoten, bei denen das Label mit "Function - " beginnt
    und danach das Muster NOUN VERB NOUN enthält.
    """
    count = 0  # Zähler für passende Knoten
    number_nodes = 0
    matching_nodes = []
    matching_tags = []

    NOUN_NOUN_FUNCTION = 0 
    NOUN_VERB_FUNCTION = 0
    NOUN_VERB_NOUN_FUNCTION = 0
    NOUN_NOUN_CC_VERB_FUNCTION = 0

    NP_VP_COUNTER = 0 
    PRP_NP_VP_COUNTER = 0
    COUNTER_FALSE_EVENTS = 0
    
    # POS-Tags für Nouns und Verbs definieren
    noun_tags = {'NN', 'NNS', 'NNP', 'NNPS'}
    verb_tags = {'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ'}


    
    for node in graph.get('nodes', []):
        if node['type'] == 'Function':
            number_nodes += 1
            label = node.get('label', "")

            if label.startswith("Event - "):
                COUNTER_FALSE_EVENTS += 1

            # Überprüfen, ob das Label mit "Function - " beginnt
            if label.startswith("Function - "):
                # Text nach "Function - " extrahieren
                content = label[len("Function - "):].strip()

                # Tokenisierung und POS-Tagging
                tokens = word_tokenize(content)
                pos_tags = pos_tag(tokens)

                # POS-Tag-Sequenz extrahieren
                tags = [tag for _, tag in pos_tags]

                # Überprüfen auf das Muster NOUN VERB NOUN
                for i in range(len(tags)):
                    current_pattern = tags[i:i + 4] # Hole bis zu vier aufeinanderfolgende Tags

                    if i + 2 <= len(tags):
                            match current_pattern:  
                                case [n1, a1, *_] if n1 in noun_tags and a1 in noun_tags:
                                    count += 1
                                    matching_nodes.append(node)
                                    matching_tags.append(tags)
                                    NOUN_NOUN_FUNCTION += 1
                                    NOUN_NOUN_FUNCTION_list.append(tags)
                                    NP_VP_COUNTER += 1
                                    break

                                case [n1, a1, *_] if n1 in noun_tags and a1 in verb_tags:
                                    if not tokens[i + 1].endswith("ed"):
                                        count += 1
                                        matching_nodes.append(node)
                                        matching_tags.append(tags)
                                        NOUN_VERB_FUNCTION += 1
                                        NOUN_VERB_FUNCTION_list.append(tags)
                                        NP_VP_COUNTER += 1
                                        break

                    if i + 3 <= len(tags):
                            match current_pattern:  
                                case [n1, a1, v1, *_] if n1 in noun_tags and a1 in verb_tags and v1 in noun_tags:
                                    if not tokens[i + 1].endswith("ed"):
                                        count += 1
                                        matching_nodes.append(node)
                                        matching_tags.append(tags)
                                        NOUN_VERB_NOUN_FUNCTION += 1
                                        NOUN_VERB_NOUN_FUNCTION_list.append(tags)
                                        NP_VP_COUNTER += 1  
                                        break

                    if i + 4 <= len(tags):
                            match current_pattern:  
                                case [n1, n2, c1, v1,*_] if n1 in noun_tags and n2 in noun_tags and c1 =='CC' and v1 in noun_tags:
                                    if not tokens[i + 1].endswith("ed"):
                                        count += 1
                                        matching_nodes.append(node)
                                        matching_tags.append(tags)
                                        NOUN_NOUN_CC_VERB_FUNCTION += 1
                                        NOUN_NOUN_CC_VERB_FUNCTION_list.append(tags)
                                        NP_VP_COUNTER += 1
                                        break

    plot_matching_tags(matching_tags, "Function")

    COUNTER_TRUE_FUNCTIONS = NP_VP_COUNTER + PRP_NP_VP_COUNTER

    return number_nodes, count, matching_nodes, COUNTER_TRUE_FUNCTIONS, COUNTER_FALSE_EVENTS

def check_event_pattern(graph):
    """
    Zählt die Knoten, bei denen das Label mit "Event - " beginnt
    und danach das Muster NOUN VERB NOUN enthält.
    """
    count = 0  # Zähler für passende Knoten
    number_nodes = 0
    matching_nodes = []
    matching_tags = []

    NOUN_AUX_EVENT = 0
    NOUN_VERB_EVENT = 0
    ADJ_NOUN_VERB_EVENT = 0
    NOUN_AUX_VERB_EVENT = 0
    NOUN_NOUN_VERB_EVENT = 0
    NOUN_AUX_VERB_NOUN_EVENT = 0
    NOUN_VERB_VERB_EVENT = 0

    NP_VP_COUNTER = 0 
    NP_VP_PRP_COUNTER = 0
    FALSE_FUNCTION =0
    
    # POS-Tags für Nouns und Verbs definieren
    noun_tags = {'NN', 'NNS', 'NNP', 'NNPS'}
    aux_tags = {'MD', 'VBZ', 'VBP', 'VBG', 'VBD', 'VBN', 'TO'}
    verb_tags = {'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ'}
    adjective_tags = {'JJ','JJS','JJR'}
    
    for node in graph.get('nodes', []):

        if node['type'] == 'Event' and node['patternType'] != 'StartEPC' and node['patternType'] != 'EndEPC':
            number_nodes += 1
            label = node.get('label', "")

            # Überprüfen, ob das Label mit "Event - " beginnt
            if label.startswith("Function -"):
                FALSE_FUNCTION += 1
            if label.startswith("Event - ") and "Function -" not in label:
                # Text nach "Function - " extrahieren
                content = label[len("Event - "):].strip()
                content = remove_punctuation_and_percent(content)
                
                # Tokenisierung und POS-Tagging
                tokens = word_tokenize(content)
                pos_tags = pos_tag(tokens)
                # POS-Tag-Sequenz extrahieren
                tags = [tag for _, tag in pos_tags]

                # Überprüfen auf das Muster NOUN AUX VERB NOUN
                for i in range(len(tags)):  # Sicherstellen, dass mindestens 4 Tags geprüft werden können
                    current_pattern = tags[i:i + 4] # Hole bis zu vier aufeinanderfolgende Tags


                    if i + 2 <= len(tags):
                            match current_pattern:  
                                case [n1, a1, *_] if n1 in noun_tags and a1 in aux_tags:
                                    matching_nodes.append(node)
                                    matching_tags.append(tags)
                                    count += 1
                                    NOUN_AUX_EVENT += 1
                                    NOUN_AUX_EVENT_list.append(tags)
                                    break

                                case [n1, v1, *_] if n1 in noun_tags and v1 in verb_tags:
                                    if tokens[i + 1].endswith("ed"): 
                                        matching_nodes.append(node)
                                        matching_tags.append(tags)
                                        count += 1
                                        NOUN_VERB_EVENT += 1
                                        NOUN_VERB_EVENT_list.append(tags)
                                        NP_VP_COUNTER += 1
                                        break

                    if i + 3 <= len(tags):
                        match current_pattern:  
                            case [adj, n1, v1, *_] if adj in adjective_tags and n1 in noun_tags and v1 in verb_tags:
                                matching_nodes.append(node)
                                matching_tags.append(tags)
                                count += 1
                                ADJ_NOUN_VERB_EVENT += 1
                                ADJ_NOUN_VERB_EVENT_list.append(tags)
                                break


                            case [n1, a1, v1, *_] if n1 in noun_tags and a1 in aux_tags and v1 in verb_tags:
                                matching_nodes.append(node)
                                matching_tags.append(tags)
                                count += 1
                                NOUN_AUX_VERB_EVENT += 1
                                NOUN_AUX_VERB_EVENT_list.append(tags)
                                NP_VP_PRP_COUNTER +=1
                                break

                            case [n1, n2, v1, *_] if n1 in noun_tags and n2 in noun_tags and v1 in verb_tags:
                                matching_nodes.append(node)
                                matching_tags.append(tags)
                                count += 1
                                NOUN_NOUN_VERB_EVENT += 1
                                NOUN_NOUN_VERB_EVENT_list.append(tags)
                                NP_VP_COUNTER += 1
                                break

                            case [n1, v1, v2, *_] if n1 in noun_tags and v1 in verb_tags and v2 in verb_tags:
                                matching_nodes.append(node)
                                matching_tags.append(tags)
                                count += 1
                                NOUN_VERB_VERB_EVENT += 1
                                NOUN_VERB_VERB_EVENT_list.append(tags)
                                NP_VP_COUNTER += 1
                                break

                    if i + 4 <= len(tags):    
                        match current_pattern:
                            case [n1, a1, v1, n2] if n1 in noun_tags and a1 in aux_tags and v1 in verb_tags and n2 in noun_tags:
                                matching_nodes.append(node)
                                matching_tags.append(tags)
                                count += 1
                                NOUN_AUX_VERB_NOUN_EVENT += 1
                                NOUN_AUX_VERB_NOUN_EVENT_list.append(tags)
                                NP_VP_PRP_COUNTER += 1
                                break
    COUNTER_TRUE_EVENTS = NP_VP_PRP_COUNTER + NP_VP_COUNTER
    plot_matching_tags(matching_tags, "Event")
    return number_nodes, count, matching_nodes, COUNTER_TRUE_EVENTS, FALSE_FUNCTION


def check_label_subprocess(graph):
    """
    Zählt die richtig beschrifteten Subprozesse
    """
    count = 0  # Zähler für passende Knoten
    number_links = 0
    matching_links = []
    
    # Gates definieren
    gate_types = {'ANDGate', 'ORGate', 'XORGate'} 
    
    for node in graph.get('nodes', []):
        if node['type'] in gate_types and node['status'] == 'opening':
                key_node = node['id']
                for link in graph.get('links', []):
                    if link['source'] == key_node:
                        count += 1
                        if 'label' in link:
                            number_links += 1
                            label = link.get('label', "")
                            print(label)
                            matching_links.append(link)
        
        if node['type'] in gate_types and node['status'] == 'LOOP':
                key_node = node['id']
                for link in graph.get('links', []):
                    if link['source'] == key_node:
                        count +=1
                        if 'label' in link:
                            number_links += 1
                            label = link.get('label', "")
                            print(label)
                            matching_links.append(link)
    
    return number_links, count, matching_links

# Example usage with the provided JSON data structure
# Assuming the file content is stored in `data`


def plot_matching_tags(matching_tags,POS_NAME):
        # Konvertiere jede Sub-Liste in ein Tupel
    sequences = [tuple(sublist) for sublist in matching_tags]

    # Häufigkeit der Sequenzen zählen
    sequence_counts = Counter(sequences)

    # Daten für das Plot vorbereiten
    sequences = [' '.join(seq) for seq in sequence_counts.keys()]  # Konvertiere Tupel zu Strings für bessere Lesbarkeit
    counts = list(sequence_counts.values())

    # Plot erstellen
    plt.figure(figsize=(12, 6))
    bars = plt.bar(sequences, counts, color='skyblue', edgecolor='black')
    plt.xlabel(f'POS-Sequenzen von {POS_NAME}', fontsize=12)
    plt.ylabel('Häufigkeit', fontsize=12)
    plt.title(f'Häufigkeit von {POS_NAME}', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=10)  # Drehe die Labels für bessere Lesbarkeit
    plt.yticks(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    # Absolute Anzahl auf die Balken schreiben
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, str(count), ha='center', va='bottom', fontsize=10, color='black')

    # Plot anzeigen
    #plt.show()

with open('llama_1b/modified_graph_9.json') as file: # Users/fabiankassner/Documents/3 Semester/FuE_2/llama_1b/sharding_2/results/
    data = json.load(file)


number_event_nodes, event_count, matching_event_nodes, counter_true_events, counter_false_functions = check_event_pattern(data)
percentage_event = "{}%".format((round((event_count/number_event_nodes)*100,4)))
print(percentage_event)
print("Anzahl an Knoten die als Event gekennzeichnet sind: ", number_event_nodes, "Anzahl der richtig beschrifteten Events: ", event_count)

number_function_nodes, function_count, matching_function_nodes, counter_true_functions, counter_false_events = check_function_pattern(data)
percentage_function = "{}%".format((round((function_count/number_function_nodes)*100,4)))
print(f"Percentage of nodes labeled: {percentage_function}")
print("Anzahl an Knoten die als Function gekennzeichnet sind: ", number_function_nodes, "Anzahl der richtig beschrifteten Functions: ", function_count)

# Richtig beschriftete Graphen


# Berechnung von Accuracy, Precision, Recall, F-Maß für events
# Gesamtzahl von Events und Funktionen ist voneinander unabhängig
true_positives = counter_true_events
true_negatives = counter_true_functions
false_positives = counter_false_events
false_negatives = counter_false_functions

# Precision = TP / (TP + FP)
#precision = true_positives / (true_positives + false_positives)
#print(f"Precision: {precision}")
#print("-----------------------")

## Recall = TP / (TP + FN)
#recall = true_positives / (true_positives - false_negatives)
#print(f"Recall: {recall}")
#print("-----------------------")

## Accuracy = (TP + TN) / (TP + TN + FP + FN)
#accuracy = (true_positives + true_negatives) / (true_positives + true_negatives + false_positives + false_negatives)
#print(f"Accuracy: {recall}")
#print("-----------------------")

## F-Maß = 2 * (Precision * Recall) / (Precision + Recall)
#f_maß = 2 * ((precision * recall) / (precision + recall))
#print(f"F-Maß: {f_maß}")
#print("-----------------------")

#number_links, count, matching_links = check_label_subprocess(data)
#print(f"Anzahl an Subprozessen die gekennzeichnet sind:  {count} Anzahl der richtig beschrifteten Subprozesse: {number_links}")