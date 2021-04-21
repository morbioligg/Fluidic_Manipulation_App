# -*- coding: utf-8 -*-
"""
Created on Sat Jan 19 11:33:16 2019

@author: morbioli
Written by Giorgio Morbioli for the Stockton Group at the Georgia Institute of Technology
It uses parts of the Dijkstra algorithm developed by  redblobgames@gmail.com

"""
#import the necessary libraries
import heapq 
import ast
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter import *
from tkinter import ttk
import re
import PIL.Image
import PIL.ImageTk
import pyfirmata
from pyfirmata import ArduinoMega
import time
import pickle


#tools to draw the grid that represents the processor on the screen
def draw_tile(graph, id, style, width):
    r = "."
    if 'number' in style and id in style['number']: r = "%d" % style['number'][id]
    if 'point_to' in style and style['point_to'].get(id, None) is not None:
        (x1, y1) = id
        (x2, y2) = style['point_to'][id]
    if 'start' in style and id == style['start']: r = "S"
    elif 'goal' in style and id == style['goal']: r = "G"
    elif 'path' in style and id in style['path']: r = "@"
    elif 'path1' in style and id in style['path1']: r = "&"
    if id in graph.walls: r = "#"
    elif id in (graph.blocked_perimeter): r = "X"
    elif id in (graph.blocked_valves): r = "X"
    return r

#draws the grid of the processor on the screen
def draw_grid(graph, width=3, height = 3, **style): 
    for y in range(graph.height):
        for x in range(graph.width):
            print("%%-%ds" % width % draw_tile(graph, (x, y), style, width), end="")
        print()

#Class to set the rules for the processor
class SquareGrid:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.walls = []
        self.perimeter_valves = {}
        self.valves_positioning = {}
        self.reservoirs = []
        self.blocked_perimeter = []
        self.blocked_valves = []
        self.open = []

    
    #sets the boundaries for the grid
    def in_bounds(self, id):
        (x, y) = id
        return 0 <= x < self.width and 0 <= y < self.height
    
    #shows which valves are available
    def passable(self, id):
        if id not in self.walls:
            if id not in self.blocked_perimeter:
                if id not in self.blocked_valves:
                    return id

    #calculates which valves are neighbors of the active valve
    def neighbors(self, id):
        (x, y) = id
        
        results = [(x+1, y), (x, y-1), (x-1, y), (x, y+1)]

         
        # used to block fluidic contact between perimeter valves and reservoirs
        if (x,y) in (list(self.perimeter_valves.values())) or (list(self.reservoirs.values())):             
            if x == 0 or x == 1 or x == (self.width-2) or x == (self.width-1) :
                results = [(x+1, y), (x-1, y)]

            if y == 0 or y == 1 or y == (self.height-2) or y == (self.height-1):
                results = [(x, y-1), (x, y+1)]
                

        if (x + y) % 2 == 0: results.reverse() # aesthetics
        
        
        results = filter(self.in_bounds, results)
        results = filter(self.passable, results)
        return results

#Class to include weights in specific nodes in the graph
class GridWithWeights(SquareGrid):
    def __init__(self, width, height):
        super().__init__(width, height)
        self.weights = {}
    
    def cost(self, from_node, to_node):
        return self.weights.get(to_node, 1)

#Class needed for the Dijkstra algorithm
class PriorityQueue:
    def __init__(self):
        self.elements = []
    
    def empty(self):
        return len(self.elements) == 0
    
    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))
    
    def get(self):
        return heapq.heappop(self.elements)[1]


def dijkstra_search(graph, start, goal):
    '''Finds the path with the smallest cost between two given points in a grid'''
    frontier = PriorityQueue()
    frontier.put(start, 0)
    came_from = {}
    cost_so_far = {}
    came_from[start] = None
    cost_so_far[start] = 0
    
    while not frontier.empty():
        current = frontier.get()

        #early exit - when the shortest path is found, the algorithm stops
        if current == goal:
            break
        
        for next in graph.neighbors(current):

            new_cost = cost_so_far[current] + graph.cost(current, next)
                           
            if next not in cost_so_far or new_cost < cost_so_far[next]:
                cost_so_far[next] = new_cost
                priority = new_cost
                frontier.put(next, priority)
                came_from[next] = current
        
    return came_from

def reconstruct_path(came_from, start, goal):
    '''Using the results from the Dijkdtra algorithm, returns the path with the smaller cost'''
    current = goal
    path = []
    while current != start:
        path.append(current)
        current = came_from[current]
    path.append(start) # optional
    path.reverse() # optional    
    
    return path


def heuristic(a, b):
    '''Calculates the distance between two nodes in a graph'''
    try:
        (x1, y1) = a
        (x2, y2) = b
    except TypeError:
        MsgBox = tk.messagebox.showerror(title='Output error', message='Please, include a valid output')
        
    
    return abs(x1 - x2) + abs(y1 - y2)

def position_grid(valve):
    '''returns the coordinates of a specific valve in the grid 
    using the valve number'''
    if valve in my_processor.reservoirs:
        return my_processor.reservoirs[valve]
    elif valve in my_processor.valves_positioning:
        return my_processor.valves_positioning[valve]
    elif valve in my_processor.perimeter_valves:
        return my_processor.perimeter_valves[valve]


def avoid(*argv):
    '''Eliminates non-working valves from consideration to be used in the processor'''
    set_valves = set()
    set_perimeter = set()
    
    for arg in argv:
        valve = str(arg)
        
        if valve in my_processor.valves_positioning:
            positioning = position_grid(valve)
            set_valves.add(positioning)
        
        elif valve in my_processor.perimeter_valves:
            peri = position_grid(valve)
            set_perimeter.add(peri)
        
    my_processor.blocked_perimeter = list(set_perimeter)
    my_processor.blocked_valves = list(set_valves)
            
    return my_processor.blocked_perimeter,my_processor.blocked_valves


def change_name(old_key,new_key):
    ''' Changes the name of a reservoir'''
    my_processor.reservoirs[new_key] = my_processor.reservoirs.pop(old_key)
    
    return my_processor.reservoirs


def available_neighbor(valve,my_processor,all_steps):
    '''Return a list of neighboring valves of the processor from of a specific valve'''
    available = []
    neig = list(my_processor.neighbors(valve))

    for n in neig:
        if n in my_processor.valves_positioning.values():
            if n not in my_processor.open:
                if n not in  my_processor.blocked_perimeter:
                    if n not in my_processor.blocked_valves:
                        if n not in all_steps:
                            available.append(n)
                            
    return available

def select_whos_closer(available, goal,my_processor,all_steps,stop_valve_input):
    '''From a list of available valves, returns the valve that is closer to the goal'''
    
    distances = [heuristic(valve,goal) for valve in available]
    
    if len(available) != 0:
        ind = distances.index(min(distances))
        valve = available[ind]
    
        return valve
    
    else:

        available = list(set(my_processor.valves_positioning.values()) - set(my_processor.open) - set(all_steps)-set(my_processor.blocked_valves))

        distances = [heuristic(valve,stop_valve_input) for valve in available]
        
        try:
            ind = distances.index(min(distances))
            valve = available[ind]
        except:
            MsgBox = tk.messagebox.showerror(title='Input error', message='Wrong number of valves opened. Please, press restart')
    
        return valve
        
def checking_closing(my_processor, closing):
    '''Checks if there is a complete fluidic path to the output from the current valve, and changes valves positioning until it does'''
    
    for i in range(len(closing)-1):
        testing = closing[i:]
        any_neigh = any(valve in (my_processor.neighbors(testing[0])) for valve in testing) 

        if any_neigh != True:

            closing[i-1],closing[i] = closing[i],closing[i-1]
            
            return checking_closing(my_processor, closing)
    
    return closing

#INFO RELEVANT FOR THE SPECIFIC PROCESSOR
    
#size of the grid that can contain all features
Original_path = os.getcwd()
New_folder = r'\Processor_info'
os.chdir(Original_path + New_folder)
inf = open('size.txt','r')
size = ast.literal_eval(inf.read())
inf.close()
width = size[0]
height = size[1]

my_processor = GridWithWeights(width, height)

#definition of the nodes that do not codify a valve
#Will be represented as # in the grid
inf1 = open('walls.txt','r')
my_processor.walls = ast.literal_eval(inf1.read())
inf1.close()

#dictionary containing the reservoir name as the key for the node they code
# these are not valves and therefore CANNOT BE ACTUATED
inf2 = open('reservoirs.txt','r')
my_processor.reservoirs = ast.literal_eval(inf2.read())
inf2.close()

#dictionary containing the perimeter valve name as the key for the node they code
#Perimeter valves do not have connections in all directions, and act as bridges
#between the reservoirs and the processor
inf3 = open('perimeter_valves.txt','r')
my_processor.perimeter_valves = ast.literal_eval(inf3.read())
inf3.close()

#dictionary containing the valve name as the key for the node they code
#These are the valves of the processor
inf4 = open('valves_positioning.txt','r')
my_processor.valves_positioning =  ast.literal_eval(inf4.read())
inf4.close()

#dictionary containing the pins of the Arduino that will actuate a specific solenoid valve   
inf5 = open('Arduino_pins.txt','r')
Python_to_arduino =  ast.literal_eval(inf5.read())
inf5.close()

os.chdir(Original_path)

def transfer(filename, output, w, description, *avoid_valves, **input_rate):
    '''Method to transfer fluid from one reservoir to another 
    using the microfluidic processor. Necessary to include: 
    1. the name of the output reservoir;
    2. the number of the valves that should be avoided 
    (can be more than one value, separated by commas; 
    it also can be empty, in the case none valves should be avoided)
    and;
    3. the inputs with their respective ratios ({valve1:ratio1,valve2:ratio2...});
    to move fluid from one input to the output, just use one input and one ratio'''
    
    #This is run in the case there are no inputs or outputs; it is required to provide a waiting time between processes
    #Setting wait time; 
    waiting_time = int(w)
    try:
        if input_rate == {}:
            if output == '':
                os.chdir(os.getcwd() + r'\Routines')

                #Creates the file that will be read by the OTHER software
                routine = ['w']               
                file_name = str(filename)
                
                i=1
                while os.path.exists(os.getcwd() + '\\' + file_name + ".py") == True:
                    file_name = file_name + '(' + str(i) + ')'
                    i = i+1
            
                file = open(file_name+".py","w") 
                
                
                #makes the list that will be read by OTHER software
                file.write('from ocwcomposer import *\n')
                #if sequence description is needed, uncomment this line
                seq_desc = str(description)
                file.write('seq1 = Sequence("' + seq_desc + '",')
                #file.write('seq1 = Sequence("' + '",')
                file.write('    SetDefaultWait(%i),'% waiting_time)
                for item in routine:
                    file.write (item.strip('"\''))
                file.write(')')
            
                file.close()
                
                cwd = os.getcwd()
                final_dest = str(cwd + '\\' + file_name + '.py')
                final_name = str(file_name)
                

                return final_dest, routine, final_name
                            
    except:
        pass
    
    # It avoids that non-working valves can be used to move fluids
    avoid(*avoid_valves)
    
    #sets the output
    output_ = position_grid(str(output))
    #stop_valve_output = list(my_processor.neighbors(output_))[0]

    #Operating the valves
    
    #checking if the number of valves required is equal or smaller than the
    #number of valves available in the processor, and also if the input and the output are the same
    value_total = 0
    
    #Sorts the inputs by the number of valves required 
    #Smaller number of valves is selected first
    inputs = sorted(input_rate.items(), key=lambda kv: kv[1])
    
    
    for key, value in inputs:
        #checking if the input and the output are the same - Maybe remove it if implementing the 
        #complementary mixing function
        if key == output:
            MsgBox = tk.messagebox.showerror(title='Input error', message='The input and the output are the same. Please, restart.')
            #raise Exception("The input and the output are the same")
        
        value_total = value_total + value

        valves_available = (len(my_processor.valves_positioning)- len(my_processor.blocked_valves))
    
        if value_total > valves_available:
            MsgBox = tk.messagebox.showerror(title='Input error', message='There are more valves required by the inputs than valves available in the processor.')
            #raise Exception("There are more valves required by the inputs than valves available in the processor")
    
    #Check for the shortest path for all the valves
    groups = {}
    
    for key, value in inputs:
        input_ = position_grid(str(key))        
        stop_valve_input = list(my_processor.neighbors(input_))[0]
        all_steps = []

        valve = stop_valve_input            
        while len(all_steps)<value:
            available = available_neighbor(valve,my_processor,all_steps)
            valve = select_whos_closer(available, output_,my_processor,all_steps,stop_valve_input)
            all_steps.append(valve)
        
        groups.update({key:all_steps})
        my_processor.open.extend(all_steps)
        
        #Draw grid for the opened valves
        #draw_grid(my_processor, path=(all_steps), start=(input_),goal=(output_), width=3, height = 8 )
        #print(25*'-')


    if len(my_processor.open)!= value_total:
        #raise Exception("Wrong number of valves opened")
        MsgBox = tk.messagebox.showerror(title='Input error', message='Wrong number of valves opened. Please, press restart')
            

    
    #opens the valves from the output to the first set of open valves
    to_close = []
    distance = []
    
    #creates a list of which valves are going to be opened 
    #from the outlet towards the other group of valves
    contact = []
    available2 = list(set(my_processor.valves_positioning.values()) - set(my_processor.open) -set(my_processor.blocked_valves))
    
    
    #Changes valves coordinates into their names (info codified in the dictionary)
    opening_by_name = []
    for key in groups.keys():
        list_a = groups[key]
        
        distances1 = []
        for node in list_a:
            distance_node = (heuristic(node,output_),(node),key)
            distances1.append(distance_node)
        
        organized = sorted(distances1, key=lambda x: x[0])
        
        distance.append(organized)
    
        #opens the valves by name instead of position
        opening_by_name.append('o' + list(my_processor.perimeter_valves.keys())[list(my_processor.perimeter_valves.values()).index((list(my_processor.neighbors(position_grid(str(key))))[0]))] +',' + 'w,')
        
        
        
        for valve_position in list_a:
            value = list(my_processor.valves_positioning.keys())[list(my_processor.valves_positioning.values()).index(valve_position)]
            
            string =  'o' + value +',' + 'w,'
            
            opening_by_name.append(string)
        
        
        opening_by_name.append('c' + list(my_processor.perimeter_valves.keys())[list(my_processor.perimeter_valves.values()).index((list(my_processor.neighbors(position_grid(str(key))))[0]))] +',' + 'w,')
        
        
    
    #Make a list to open the valves in the correct order
    organized2 = sorted(distance, key=lambda x: x[0][0])
    
    came_from2 = (dijkstra_search(my_processor, output_,organized2[0][0][1]))
    all_steps2 = reconstruct_path(came_from2, output_, organized2[0][0][1])[2:-1]


    new = groups.pop(organized2[0][0][2])

    for v in all_steps2:
        if v in available2:
            my_processor.open.append(v)
            new.append(v)
            to_close.append(v)
            contact.append(v)
    
    sorting = organized2[0][0][2]

    for i in organized2[0]:
        if i[2] == sorting:
            to_close.append(i[1])
    
    opening_by_name2 = []
    try:
        opening_by_name2.append('o' + list(my_processor.perimeter_valves.keys())[list(my_processor.perimeter_valves.values()).index((list(my_processor.neighbors(position_grid(str(output))))[0]))] +',' + 'w,')
    except ValueError:
        MsgBox = tk.messagebox.showerror(title='Output error', message='Please, include a valid output')
        
    
    while groups !={}:
    
        
    #opens the valves from the first set of open valves connected to the output to the 
    #next set of open valves 
        distance_total =[]
        
        for node1 in new:
            distances2 = []
            for key in groups.keys():
                lista2 = groups[key]
            
                for node2 in lista2:
                    distance_node1 = (heuristic(node1,node2),(node1),(node2),key)
                    distances2.append(distance_node1)
                
            organized3 = sorted(distances2, key=lambda x: x[0])
            
            distance_total.append(organized3)
        organized4 = sorted(distance_total, key=lambda x: x[0][0])
        
        
        came_from3 = (dijkstra_search(my_processor, organized4[0][0][1],organized4[0][0][2]))
        all_steps3 = reconstruct_path(came_from3, organized4[0][0][1],organized4[0][0][2])[1:-1]
    
        new = groups.pop(organized4[0][0][3])

        for v in all_steps3:
            if v in available2:
                my_processor.open.append(v)
                new.append(v)
                to_close.append(v)
                contact.append(v)

    
        sorting2 = organized4[0][0][3]
        
        for i in organized4[0]:
            if i[3] == sorting2:
                to_close.append(i[2])
    

    #opens the valves by name instead of position
    for valve_position2 in contact:
        value = list(my_processor.valves_positioning.keys())[list(my_processor.valves_positioning.values()).index(valve_position2)]
        
        string = 'o' + value +',' + 'w,'
           
        opening_by_name2.append(string)

    #reverses the closing list to end it with the output
    closing = to_close[::-1]
    
    #Checks if there is a fluidic path between the valves during the closing step
    checking_closing(my_processor, closing)
    
    #Draws the grids on screen
    #draw_grid(my_processor, path=(my_processor.open), start=(),goal=(output_), width=3, height = 8 )
    #print(25*'-')
    
    #Returns the valves by numbers / names instead of their position in the grid
    closing_by_name = []
    for valve_position in closing:
        value = list(my_processor.valves_positioning.keys())[list(my_processor.valves_positioning.values()).index(valve_position)]
        
        string = 'c' + value +',' + 'w,'
        
        closing_by_name.append(string)
    
    closing_by_name.append('c' + list(my_processor.perimeter_valves.keys())[list(my_processor.perimeter_valves.values()).index((list(my_processor.neighbors(position_grid(str(output))))[0]))] +',w')
    

    #Changing the directory to save the Routines in the appropriate folder
    os.chdir(os.getcwd() + r'\Routines')

    #Creates the file that will be read by other software
    routine = []
    routine.extend(opening_by_name)
    routine.extend(opening_by_name2)
    routine.extend(closing_by_name)
 
    file_name = str(filename)
    i=1
    while os.path.exists(os.getcwd() + '\\' + file_name + ".py") == True:
        file_name = file_name + '(' + str(i) + ')'
        i = i+1
    
    file = open(file_name+".py","w") 
    
    
    #makes a list that can be read by other software
    file.write('from ocwcomposer import *\n')
    #if sequence description is needed, uncomment this line
    seq_desc = str(description)
    file.write('seq1 = Sequence("' + seq_desc + '",')
    #file.write('seq1 = Sequence("' + '",')
    file.write('    SetDefaultWait(%i),'% waiting_time)
    for item in routine:
        file.write (item.strip('"\''))
    file.write(')')

    file.close()
    
    cwd = os.getcwd()
    final_name = str(file_name)
    final_dest = str(cwd + '\\' + file_name + '.py')
    final_name = str(file_name)

    return final_dest, routine,final_name
    

#Here the GUI information goes

def main(path_given):
    global master
    master = Tk()
    master.title('Automatic Fluidic Manipulation Application')
    master.geometry("1050x725")
    
    nb = ttk.Notebook(master)
    nb.grid(row=1, column = 0, columnspan = 50,rowspan = 55, sticky = 'NESW')
    
    page1 = ttk.Frame(nb)
    nb.add(page1, text = 'Routine')
    
    
    def ExitApplication():
            '''defines what the Exit Application button does'''
            MsgBox = tk.messagebox.askquestion ('Exit Application','Are you sure you want to exit the application',icon = 'warning')
            if MsgBox == 'yes':
                try:
                    board.exit()
                except:
                    pass
                    
                master.destroy()
    
    
    def separate(text):
        '''separate the info'''
        
        without_space = text.replace(" ", "")
        sentences = re.split(r'[,;]+', without_space)
        
        d = {}
        if sentences != ['']:
            for item in sentences:
                valve = str(item.split(':')[0]).upper()
                try:
                    number = int(item.split(':')[1])
                    d[valve] = number
                except IndexError:
                    MsgBox = tk.messagebox.showerror(title='Input error', message='Please, add valve to be used in the format A : Number') 
        else:
            pass
        
        return d

    def clear_text(thing):
            thing.delete(0,'end')    
        
    Label(page1, text="Fluidic Processor").grid(row=0, sticky=W)
    Label(page1, text='File Name').grid(row=1)
    Label(page1, text='Inputs').grid(row=2) 
    Label(page1, text='Output').grid(row=3)
    Label(page1, text='Avoid').grid(row=4)
    Label(page1, text='Wait time (ms)').grid(row=5)
    Label(page1, text='Sequence description').grid(row=10)
    #Label(page1, text='Number of repetitions').grid(row=6)
    #Label(master, text='Number of repetitions').grid(row=0, column = 4, rowspan = 8)
    
    e0 = Entry(page1)
    e1 = Entry(page1) 
    e2 = Entry(page1) 
    e3 = Entry(page1)
    e4 = Entry(page1)
    #e5 = Entry(page1)
    e6 = Entry(page1,width=30)
    
    e0.grid(row=1, column=1)
    e1.grid(row=2, column=1) 
    e2.grid(row=3, column=1)
    e3.grid(row=4, column=1)
    e4.grid(row=5, column=1)
    #e5.grid(row=6, column=1)
    e6.grid(row=11, column=0, columnspan = 3)
    #e6.place(width=150,height=50)
    var1 = IntVar() 
    #var2 = IntVar()
    
    def refresher():
        clear_text(e0)
        clear_text(e1)
        clear_text(e2)
        clear_text(e3)
        clear_text(e4)
        clear_text(e6)
        
        refresh()
    
    def Run():
        

        value_e0 = str(e0.get())
        value_e1 = (e1.get())
        value_e2 = str(e2.get()).upper()
        value_e3 = e3.get()
        value_e4 = e4.get()
        value_e6 = e6.get()
        
        if value_e4 == '':
            value_e4 = 300
        
        if value_e0 == '':
            value_e0 = 'No_name_routine'

         
        dict1 = separate(value_e1)
        
        
        avoid = []
        if value_e3 == '':
            pass
        
        else:
            without_space = value_e3.replace(" ", "")
            sentences = re.split(r'[,;]+', without_space)
            for item in sentences:
                try:
                    evitar = int(item)
                    avoid.append(evitar)
                except ValueError:
                    MsgBox = tk.messagebox.showerror(title='Avoid valve error', message='If input / output is unavailable, select another')
                    

        path_total = transfer(str(value_e0),value_e2,value_e4,value_e6, *avoid,**dict1)
        path_file = path_total[0]
        
        lbox.insert(tk.END, path_total[2] + '.py')
        
        arduino_list = []
        for item in path_total[1]:
            inside = re.split(r'[,;]+', item.replace(" ", ""))
            for item2 in inside:
                if item2 != '':
                    arduino_list.append(item2)


        #restarts the program after running the sequence
        refresher()
        

    
    #Tab1
    Running = Button(page1, text ='Run', fg ='black', command = Run).grid(row=8, column=0, sticky=W)
    Restarting = Button(page1, text ='Restart', fg ='black', command=refresher).grid(row=8, column=1, sticky=W)
    Exit = Button(page1, text ='Exit Application', fg ='black', command = ExitApplication).grid(row=8, column=2, sticky=W)
    
    
    image_path = path_given + r'\Processor_info\chip.png'
    
    
    Label(page1, text="Fluidic Processor").grid(row=0, sticky=W)
    ref = PIL.Image.open(image_path)
    photo = PIL.ImageTk.PhotoImage(image = ref)
    Label(page1,image=photo).grid(row=0,column=4, rowspan = 32)
    
    #Tab2
    page2 = ttk.Frame(nb)
    nb.add(page2, text = 'Methods') 
    

    def add_name():
        if len(lbox.curselection()) != 0:
            x = lbox.get(lbox.curselection())
            lbox2.insert(END, x)
        else:
            pass
    
    
    def remove_name():
        if len(lbox2.curselection()) != 0:
            lbox2.delete(lbox2.curselection())
        else:
            pass
        
    def updating():
        refresh2()
    
    Label(page2, text='Method Name').grid(row=6,column=3)         
    e7 = Entry(page2)
    e7.grid(row=6, column=4)
    
    #Tab3
    page3 = ttk.Frame(nb)
    nb.add(page3, text = 'Arduino')
    
    # Selected routines
    Label(page3, text="Available Methods").grid(row=0, column = 4, sticky=W)
    lbox3 = tk.Listbox(page3, height = 20, width = 50)
    lbox3.grid(row = 1, column =4, rowspan = 5, sticky=(N,W,E,S))
    d = ttk.Scrollbar(page3, orient=VERTICAL, command=lbox3.yview)
    d.grid(column=5, row=1, rowspan = 5, sticky=(N,S))
    lbox3['yscrollcommand'] = d.set
        
    # get the list of files
    Label(page2, text="Available Routines").grid(row=0, column = 1, sticky=W)
    flist = os.listdir(os.getcwd() + r'\Routines')
    # Available routines
    lbox = tk.Listbox(page2, height = 20, width = 50)
    lbox.grid(row = 1, column =1,rowspan = 5,  sticky=(N,W,E,S))
    s = ttk.Scrollbar(page2, orient=VERTICAL, command=lbox.yview)
    s.grid(column=2, row=1, rowspan = 5, sticky=(N,S))
    lbox['yscrollcommand'] = s.set

    # THE ITEMS ARE INSERTED WITH A LOOP
    lbox.delete(0, END)
    for item in flist:
        if str(item).endswith('.py'):
            lbox.insert(tk.END, item)

    
    # Selected routines
    Label(page2, text="Selected Routines").grid(row=0, column = 4, sticky=W)
    lbox2 = tk.Listbox(page2, height = 20, width = 50)
    lbox2.grid(row = 1, column =4, rowspan = 5, sticky=(N,W,E,S))
    s = ttk.Scrollbar(page2, orient=VERTICAL, command=lbox2.yview)
    s.grid(column=5, row=1, rowspan = 5, sticky=(N,S))
    lbox2['yscrollcommand'] = s.set


    add_button = Button(page2, text='Add', command=add_name).grid(row = 2, column =3)
    remove_button = Button(page2, text='Remove', command=remove_name).grid(row = 3, column =3)
    Exit = Button(page2, text ='Exit Application', fg ='black', command = ExitApplication).grid(row=8, column=5, sticky=W)
    #Restarting = Button(page2, text ='Restart', fg ='black', command=self.update_idletasks).grid(row=8, column=1, sticky=W)

    def opening(path):
            
        item = path
        sequence = os.path.join(os.getcwd(), r'Routines\\' + str(item))
        file_object1 = open(sequence,'r')
        info1 = file_object1.readlines()
        without_stuff = (info1[1].split('SetDefault',)[1])[:-1]
        separated_into_commands = re.split(r'[,]+', without_stuff)
        Waitingtime = separated_into_commands.pop(0)
        Waiting_time =int(''.join(filter(str.isdigit, Waitingtime)))
        
        new = []
        for item in separated_into_commands:
            item.strip()
            
            if item.startswith('w'):
                thing = item+str(Waiting_time)
                new.append(thing)
            else:
                new.append(item)
        
    
        return new

    def refresher4():
        refresh()
        clear_text(e7)
        lbox2.delete(0, END)


    def select_all():
        value_e7 = str(e7.get())
        if value_e7 == '':
            value_e7 = 'No_name_method'
        
        
        items = lbox2.get(0, END)
        final_process = []
        for item in items:
            final_process.extend(opening(item))
        
        os.chdir(os.path.join(os.getcwd(), r'Routines\\Methods'))
        i=1
        while os.path.exists(os.getcwd() + '\\' + value_e7 + ".txt") == True:
            value_e7 = value_e7 + '(' + str(i) + ')'
            i = i+1
        
        file2 = open(value_e7 +".txt","w") 
        
        for item in final_process:
            file2.write (item)
            file2.write (' ')
    
        file2.close()
        
        name = value_e7 + ".txt"
        lbox3.insert(tk.END, name)

        refresher4()
        
        return final_process

        
    Do_stuff = Button(page2, text ='Save Method', fg ='black', command = select_all).grid(row=7, column=4, sticky=W)

    
    def arduino(lists):       
        try:
            board = pyfirmata.ArduinoMega('COM3')
        except:
            pass
        
        for item in lists:
            if item.startswith("o"):
                pin_number = str(''.join(filter(str.isdigit,item)))
                #pin_on = 0
                try:
                    board.digital[Python_to_arduino.get(pin_number)].write(1)
                except:
                    pass
                print('high', Python_to_arduino.get(pin_number))
            
            if item.startswith("w"):
                waiting = int(''.join(filter(str.isdigit,item)))
                try:
                    time.sleep(waiting/1000)
                except:
                    pass
                print('wait', waiting)
            
            if item.startswith("c"):
                pin_number2 = str(''.join(filter(str.isdigit,item)))
                #pin_off = 0
                try:
                    board.digital[Python_to_arduino.get(pin_number2)].write(0)
                except:
                    pass
                print('low', Python_to_arduino.get(pin_number2))
    
        try:
            board.exit()
        except:
            pass
        
    # THE ITEMS ARE INSERTED WITH A LOOP
    flist2 = os.listdir(os.getcwd() + r'\Routines\Methods')
    lbox3.delete(0, END)
    for item in flist2:
        if str(item).endswith('.txt'):
            lbox3.insert(tk.END, item)
    
    
    def Run_method():
        
        items3 = lbox3.get(lbox3.curselection())
        os.chdir(os.getcwd() + r'\Routines\Methods')
        fp = open(str(items3),'r')
        data = [list(map(str, line.strip().split(' '))) for line in fp][0]
        fp.close()
        
        refresh()
        

        arduino(data)
        
        refresh()
     
    Running_arduino = Button(page3, text ='Run', fg ='black', command = Run_method).grid(row=7, column=4, sticky=W)
    Exit = Button(page3, text ='Exit Application', fg ='black', command = ExitApplication).grid(row=8, column=5, sticky=W)
    
    master.lift()
    master.attributes('-topmost', True)
    master.attributes('-topmost', False)
    master.mainloop()
    

path = os.getcwd()

if __name__ == '__main__':
  
    def refresh():    
        os.chdir(path)
        my_processor.blocked_perimeter = []
        my_processor.blocked_valves = []
        my_processor.open = []
        
    def refresh2():    
        master.destroy()
        os.chdir(path)
        my_processor.blocked_perimeter = []
        my_processor.blocked_valves = []
        my_processor.open = []
        main(path)

    main(path)

"""

Written by Giorgio Morbioli for the Stockton Group at the Georgia Institute of Technology
It uses parts of the Dijkstra algorithm developed by  redblobgames@gmail.com
Please, cite our work if you use it for your fluidic operations

"""
