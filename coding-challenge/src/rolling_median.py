#!/usr/bin python

# Do pip install python-dateutil before execution

import sys
import os
import json
import calendar
from dateutil import parser


class User:
    """ Represents each user(vertex) in the graph.
        Uses a List to keep track of the other users(vertices)
        to which it is connected. For each neighbor added, the degree
        is incremented by 1. For each neighbor removed, the degree is
        decremented by 1.
    """
    def __init__(self, user):
        self.user = user
        self.neighbors = []
        self.degree = 0

    # string representation of the user and it's neighbors
    def __str__(self):
        return str(self.user) + ": " + str(self.neighbors) + " : " + str(self.degree)

    # this is to add neighbor to an user and increment degree by 1, for each new neighbor added
    def add_neighbor(self, user):
        if self.check_neighbor_not_present(user):       # check if neighbor is already present
            self.neighbors.append(user)
            self.degree += 1

    # this is to remove neighbor of an user and decrement degree by 1, for each neighbor removed
    def remove_neighbor(self, user):
        if not(self.check_neighbor_not_present(user)):  # check if neighbor is already removed
            self.neighbors.remove(user)
            self.degree -= 1

    # this is to check if a particular neighbor is present or not and returns a boolean value
    def check_neighbor_not_present(self, user):
        if user in self.neighbors:
            return False
        else:
            return True

    # gets the current user
    def get_user(self):
        return self.user

    # gets the list of neighbors of the user
    def get_neighbors(self):
        return self.neighbors

    # gets the degree of the user
    def get_degree(self):
        return self.degree

class Edge:
    """ Holds the master list of users.
        Also provides methods for adding and connecting one user to another.
        Provides method to remove disconnected users
    """
    def __init__(self):
        self.users_dict = {}

    def __iter__(self):
        return iter(self.users_dict.values())

    # adds a new user into the dictionary
    def add_users(self, actor, target):
        if actor not in self.users_dict:
            self.users_dict[actor] = User(actor)

        if target not in self.users_dict:
            self.users_dict[target] = User(target)

        self.add_edge(actor, target)

    # remove user from dictionary
    def remove_user(self, user):
        del self.users_dict[user]

    # adds new edges
    def add_edge(self, frm, to):
        self.users_dict[frm].add_neighbor(to)
        self.users_dict[to].add_neighbor(frm)

    # removes edge for users outside 60-second window
    def remove_edge(self, frm, to):
        # removes the neighbors of the users in the edge
        self.users_dict[frm].remove_neighbor(to)
        self.users_dict[to].remove_neighbor(frm)

        if len(self.users_dict[frm].get_neighbors()) == 0:
            self.remove_user(frm)       # remove actor user if neighbor count is 0
        if len(self.users_dict[to].get_neighbors()) == 0:
            self.remove_user(to)        # remove target user if neighbor count is 0

    # calculates the rolling median degree for each incoming payment
    def rolling_median_degree(self):
        med_degree = 0.00
        medlist = []

        for item in self.users_dict.values():
            medlist.append(item.get_degree())

        medlist.sort()          # sort the degree list

        if len(medlist) % 2 == 0:       # even median list count
            med = (float(medlist[len(medlist)/2]) + float(medlist[len(medlist)/2 - 1]))/2
        else:                           # odd median list count
            med = float(medlist[len(medlist)/2])


        # to get precision of 2 digits after decimal place with truncation
        before_dec, after_dec = str(med).split('.')
        med_degree = float('.'.join((before_dec, after_dec[:2])))

        return "%0.2f" % med_degree


if __name__ == '__main__':
    input_pathname = sys.argv[1]            # input file
    output_pathname = sys.argv[2]           # output file
    fo = open(output_pathname, "w+")        # open outfile for writing results
    fo.seek(0, 0)                           # position at beginning of output file
    e = Edge()
    edges_list = []
    max = 0
    diff = 0
    with open(input_pathname, "r") as f:    # open input file for reading
        for line in f:                      # read the file line by line
            pmt = json.loads(line)            # load from a json payment string for parsing
            pmts_out_of_range = []
            med_degree_list = []
            edges = {}

            # check for presence of actor, target and created_time fields in each payment entry
            if "created_time" in pmt and "target" in pmt and "actor" in pmt and pmt["actor"] != pmt["target"]:
                ts = pmt["created_time"]
                timestamp = calendar.timegm(parser.parse(ts).timetuple())  # convert to timestamp in epoch format
                diff = max - timestamp
                if abs(diff) < 60 or timestamp > max:
                    actor = pmt["actor"].encode("utf-8")
                    target = pmt["target"].encode("utf-8")
                    e.add_users(actor, target)
                    edges["actor"] = actor
                    edges["target"] = target
                    edges["created_time"] = timestamp
                    # check if actor and target already present in edges_list. if so check for timestamp condition
                    k = next((i for i,d in enumerate(edges_list) if actor in d.values() and target in d.values()), None)
                    if k:
                        if timestamp > edges_list[k]["created_time"]:
                            edges_list[k]["created_time"] = timestamp
                    else:
                        edges_list.append(edges)
                    if max == 0:            # before first payment max timestamp=0
                        max = timestamp
                    elif ts > max:
                        max = timestamp     # update max timestamp
                        pmts_out_of_range = [x for x in edges_list if max-x["created_time"] >= 60] # payments out of range list
                        if len(pmts_out_of_range) > 0:  # check if any edges need to be removed
                            for pmt in pmts_out_of_range:  # loop through the list to determine edges to be removed
                                e.remove_edge(pmt["actor"], pmt["target"])  # remove the edges
                        edges_list = [x for x in edges_list if max-x["created_time"] < 60] # set to in range edge_list
                        for pmt in edges_list:
                            e.add_edge(pmt["actor"], pmt["target"])  # recalculate edges

                median = str(e.rolling_median_degree())           # calculate rolling median degree
                fo.write(median)                           # write rolling median degree to output file
                fo.write("\n")                          # write a new line to output file
                fo.seek(0, 2)                           # go to end of file
    f.close()                                       # close the input file
    fo.close()                                      # close the output file
