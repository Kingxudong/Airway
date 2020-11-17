#!/usr/bin/env python3
import csv
from pathlib import Path

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from util.util import get_data_paths_from_args

plt.rcParams.update({'font.size': 4})


def get_graph_edit_distance():
    # calculate the graph edit distance between all trees
    # okay this takes extreme long -> only for small trees nodes(tree)=12 max
    ged_dict = {}
    for pa in pat_id_list:
        for pb in pat_id_list:
            if pa == pb:
                break
            print(f"\ncalc ged from {pa} - {pb}")
            print(f"nodes: {tree_dict[pa].number_of_nodes()} <---> {tree_dict[pb].number_of_nodes()}")
            key = f"{pa}~{pb}"
            ged_dict.update({key: nx.graph_edit_distance(tree_dict[pa], tree_dict[pb])})
            print(f"{key} --> {tree_dict.get(key)}")


def longest_path_length(tree):
    d = nx.shortest_path_length(tree, source="0")
    return max([length for target, length in d.items()])


def maximum_independent_set_length(tree):
    d = nx.maximal_independent_set(tree)
    return len(d)


def create_general_tree_statistics_file(csv_path):
    if Path.exists(Path(csv_path)):
        print(f"WARNING: File was overwritten: {csv_path}")
    else:
        Path(csv_path).touch(exist_ok=False)

    with open(csv_path, 'w', newline='') as f:
        csv_writer = csv.writer(f)

        csv_writer.writerow([
            'patient',
            'nodes',
            'edges',
            'longest_path_length',
            'maximum_independent_set_length'
        ])
        stat_list = []
        for key, tree in tree_dict.items():
            curr_row = []
            curr_row.append(str(key))
            curr_row.append(tree.number_of_nodes())
            curr_row.append(tree.number_of_edges())
            curr_row.append(longest_path_length(tree))
            curr_row.append(maximum_independent_set_length(tree))
            stat_list.append(curr_row)

        csv_writer.writerows(stat_list)


def per_lobe_statistics():
    # closures
    def node_quotient():
        g = tree_dict.get(str(graph.graph['patient']))
        try:
            return g.number_of_nodes() / graph.number_of_nodes()
        except ZeroDivisionError:
            return 0

    def edges_quotient():
        g = tree_dict.get(str(graph.graph['patient']))
        try:
            return g.number_of_edges() / graph.number_of_edges()
        except ZeroDivisionError:
            return 0

    for lobe in range(2, 7):
        paths = list(input_data_path.glob('**/lobe-' + str(lobe) + '*.graphml'))

        with open(output_data_path / f"lobe-{lobe}.csv", 'w', newline='') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow([
                'patient',
                'nodes',
                'edges',
                'nodeQuotient',
                'edgeQuotient'
            ])
            for path in paths:
                graph = nx.read_graphml(path)
                csv_writer.writerow([
                    graph.graph['patient'],
                    graph.number_of_nodes(),
                    graph.number_of_edges(),
                    node_quotient(),
                    edges_quotient()
                ])


def upper_left_lobe_distance_analysis(plot_path, csv_path):
    # setup path to lobe.graphml files
    upper_left_lobe_list = input_data_path.glob('*')
    upper_left_lobe_list = [
        Path(str(patDir) + "/lobe-3-" + str(patDir.parts[-1]) + ".graphml")
        for patDir in upper_left_lobe_list
        if patDir.is_dir() and (Path(str(patDir) + "/lobe-3-" + str(patDir.parts[-1]) + ".graphml")).is_file()
    ]
    # print(len(upper_left_lobe_list))

    # fill a dicitionary with lobe graphs
    left_lobe_dict = {}
    for lobePath in upper_left_lobe_list:
        left_lobe_dict.update({lobePath.parts[-2]: nx.read_graphml(lobePath)})
    print("Found " + str(len(left_lobe_dict)) + " upper left lobes for analysis.")
    count = len(left_lobe_dict)
    not_tree_list = []
    lobe_tree_dict = {}
    # iterate over the lobes
    for key, lobe in left_lobe_dict.items():
        # print (key, nx.get_node_attributes(lobe, 'level'))

        # check if there are lobes not beeing a tree
        if not nx.is_tree(lobe):
            count = count - 1
            not_tree_list.append(key)
        else:
            lobe_tree_dict.update({key: lobe})

    print("Detected trees: " + str(count) + "/" + str(len(left_lobe_dict)))
    print("Patients whose lobes are not a tree: ")
    for tree in not_tree_list:
        print(tree)

    print("Classifying left upper lobes:")
    distance_dict = {}
    classified_counter = 0
    for key, lobe in left_lobe_dict.items():
        nodelist = []
        for node, data in lobe.nodes.items():
            nodelist.append(int(node))
        distance_value = get_distance_value(lobe, nodelist, key)
        if distance_value != (-1, -1):
            distance_dict[key] = distance_value
        if distance_value == (0, 0):
            classified_counter = classified_counter + 1
        print("-" * 70)

    print("Successfully classified " + str(classified_counter) + " lobes as Type A.")

    print("Found " + str(len(distance_dict) - classified_counter) + " potential candidates for Type B.")
    # print (distance_dict)
    # print (len(distance_dict))
    plot_distance_values(distance_dict, plot_path)
    export_classification_csv(distance_dict, csv_path)


def get_distance_value(lobe, nodelist, key):
    global dist_value
    root = min(nodelist)
    neighbour_list = list(nx.neighbors(lobe, str(root)))
    for neighbour in neighbour_list:
        if nx.get_node_attributes(lobe, 'level')[neighbour] < nx.get_node_attributes(lobe, 'level')[str(root)]:
            neighbour_list.remove(neighbour)
    neighbour_count = len(neighbour_list)
    if neighbour_count == 3:
        print(key, "classified as Type A")
        dist_value = (0, 0)
        print(neighbour_list)
    elif neighbour_count < 2:
        print(key, "Warning: less than 2 neighbours detected. Iterating....")
        nodelist.remove(root)
        if len(nodelist) != 0:
            dist_value = get_distance_value(lobe, nodelist, key)
        else:
            dist_value = (-1, -1)
    elif neighbour_count > 3:
        print(key, "Error: more than 3 neigbours detected.")
        for neighbour in neighbour_list:
            length = lobe[str(root)][neighbour]['weight']
            print("Length: " + str(length))
        dist_value = (-1, -1)
    elif neighbour_count == 2:
        print(key, "2 neighbours detected")
        weight_list = []
        for neighbour in neighbour_list:
            length = lobe[str(root)][neighbour]['weight']
            print("Length: " + str(length))
            weight_list.append(length)
        dist_value = (weight_list[0], weight_list[1])

    return dist_value


def plot_distance_values(distance_dict, path):
    patients = []
    length1_list = []
    length2_list = []
    for key, (length1, length2) in distance_dict.items():
        patients.append(key)
        length1_list.append(int(length1))
        length2_list.append(int(length2))

    x = np.arange(len(patients))
    width = 0.35
    fig, ax = plt.subplots()
    bars1 = ax.bar(x - width / 2, length1_list, width, label="Length1")
    bars2 = ax.bar(x + width / 2, length2_list, width, label="Length2")

    ax.set_ylabel('Length')
    ax.set_title('Length of edges of type B candidates')
    ax.set_xticks(x)
    ax.set_xticklabels(patients)
    ax.legend()
    autolabel(bars1, ax)
    autolabel(bars2, ax)
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')
    fig.tight_layout()

    # plt.show()
    plt.savefig(path, dpi=200)
    plt.close()


def autolabel(bars, ax):
    for bar in bars:
        height = bar.get_height()
        ax.annotate('{}'.format(height), xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3),
                    textcoords="offset points", ha='center', va='bottom')


def export_classification_csv(distance_dict, csv_path):
    if Path.exists(Path(csv_path)):
        print(f"WARNING: File was overwritten: {csv_path}")
    else:
        Path(csv_path).touch(exist_ok=False)

    with open(csv_path, 'w', newline='') as f:
        csv_writer = csv.writer(f)

        csv_writer.writerow([
            'patient',
            'classification',
            'length_1',
            'length_2',
        ])

        classification = []
        for key, (l1, l2) in distance_dict.items():
            curr_row = [str(key), get_classification(l1, l2), l1, l2]
            classification.append(curr_row)

        csv_writer.writerows(classification)


def get_classification(l1, l2):
    if (l1, l2) == (0, 0):
        return 'A'
    else:
        return 'B'


if __name__ == "__main__":
    output_data_path, input_data_path = get_data_paths_from_args()

    # paths to all trees
    path_list = [pat_dir / "tree.graphml" for pat_dir in input_data_path.glob('*') if pat_dir.is_dir()]

    lobe_id_to_string = {
        2: "LeftLowerLobe",
        3: "LeftUpperLobe",
        4: "RightLowerLobe",
        5: "RightMiddleLobe",
        6: "RightUpperLobe",
    }

    # list of all patientIDs
    pat_id_list = [pat_dir.parts[-2] for pat_dir in path_list if pat_dir.parents[0].is_dir()]

    # load all trees in dictionary (patID -> nx.graph)
    tree_dict = {}
    for tree_path in path_list:
        tree_dict.update({tree_path.parts[-2]: nx.read_graphml(tree_path)})
    print("loaded trees: " + str(len(tree_dict.keys())))

    # analysers
    create_general_tree_statistics_file(output_data_path / 'csvTREE.csv')
    per_lobe_statistics()
    upper_left_lobe_distance_analysis(output_data_path / 'type-B-edge-lengths.png',
                                      output_data_path / 'classification.csv')