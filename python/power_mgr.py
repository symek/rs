#!/usr/bin/python

from pijuice import PiJuice # Import pijuice module


pijuice = PiJuice(1, 0x14) # Instantiate PiJuice interface object
print pijuice.status.GetStatus() # Read PiJuice staus.

#turn on 12V (ramie)
print pijuice.status.GetIoDigitalInput(1)
print pijuice.status.SetIoDigitalOutput(1, 1)
#turn off 12V
print pijuice.status.GetIoDigitalInput(1)
print pijuice.status.SetIoDigitalOutput(1, 1)
print pijuice.status.GetIoDigitalInput(1)
#force select solar (0 - ratunek dla raspberry, 1 - default)
print pijuice.status.GetIoDigitalInput(2)
print pijuice.status.SetIoDigitalOutput(2, 1)
print pijuice.status.GetIoDigitalInput(2)

# TODO: Sterowanie powerswitchem)

