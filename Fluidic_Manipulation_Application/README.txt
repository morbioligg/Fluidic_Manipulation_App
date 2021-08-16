Fluidic Manipulation Application

This computer application is part of the publication by Giorgio Gianini Morbioli, Nicholas Speller, Michael Cato and Amanda Stockton, named: 
An Automated Low-Cost Modular Hardware and Software Platform for Versatile Programmable Microfluidic Device Testing and Development, available at:
https://www.sciencedirect.com/science/article/pii/S0925400521011060


## Installation

If you already have python3 installed:

```pip install pyfirmata```

## Use

The port needed to connect the Arduino Board to the computer should be COM3.
If you need to change that port for any reason, change the code to correspond to that change (line 907: board = pyfirmata.ArduinoMega('COM3'))

Open the StandardFirmata.ino file using the Arduino Application:
1 - Select your board (Tools --> Board --> Select your board)
2 - Select your port (Tools --> Port --> Select your port)
3 - Press upload (the arrow button)

To change the chip design displaying in the application, change the chip.png file in the Processor_info folder. The file should be a 700 x 700 figure.

To change the chip information, change the correspondent dictionaries on the Processor_info folder. To learn how to do so, read the manuscript and the supporting information that originated this application at the publisher's website.

Open the application (you can do that either from the command prompt or using the python IDLE of your choice) and let the computer do the hard work for you, by adding the input valves, the number of valves worth of fluid; the output valve; the waiting time between operations (default is 300 ms), and the valves to avoid (if any).

If you find this application useful, please cite our work.
