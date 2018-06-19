from .camera import Camera, Lens
from gpio.camera import Camera as Energy
class A7(Camera):
        energy = Energy()
	lens = Lens()
