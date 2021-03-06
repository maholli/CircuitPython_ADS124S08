import adafruit_sdcard 
import board, gc
from sys import path
from busio import SPI
from digitalio import DigitalInOut, Direction, Pull
from storage import mount, VfsFat
import time, neopixel_write

from analogio import AnalogIn

led       =   DigitalInOut(board.LED)
sd_cs     =   DigitalInOut(board.xSDCS)
xtb1_cs   =   DigitalInOut(board.D35)
xtb1_DRDY =   DigitalInOut(board.D36)


led.direction        =  Direction.OUTPUT
sd_cs.direction      =  Direction.OUTPUT
xtb1_cs.direction    =  Direction.OUTPUT
xtb1_DRDY.direction  =  Direction.INPUT

led.value       = 0
sd_cs.value     = 1
xtb1_cs.value   = 1


sdcard = False
filename = 'temporary'


spi = SPI(board.SCK, board.MOSI, board.MISO)
try:
    neopix = DigitalInOut(board.NEOPIXEL)
    neopix.direction = Direction.OUTPUT
except Exception as e:
    print(e)

try:
    sdcard = adafruit_sdcard.SDCard(spi, sd_cs)
    vfs = VfsFat(sdcard)
    mount(vfs, "/sd")
    path.append("/sd")
    sdcard = True
    name = 'XTB-40_000'
    files = []
    for i in range(0,100):
        filename = name[:-2]+str(int(i/10))+str(int(i%10))+'.txt'
        for j in vfs.ilistdir('/'):
            files.append(j[0])
        if filename not in files: 
            with open('/sd/'+filename, "a") as f:
                time.sleep(0.01)
            break
    print('filename is:',filename)
    sdcard = True
except Exception as e:
    print('--- SD card error ---')
    print(e)
    sdcard = False
    neopixel_write.neopixel_write(neopix, bytearray([0,255,0]))
    # pass
    while True:
        time.sleep(2)


# -------------- ADC stuff ---------------------
import ads124s08

REFERENCE_VOLTAGE = 'INTERNAL'

if REFERENCE_VOLTAGE == 'EXTERNAL':
    AVDD = 0x31
    VREF = 5.0
elif REFERENCE_VOLTAGE == 'INTERNAL':
    AVDD = 0x39
    VREF = 2.5

xtb1 = ads124s08.XTB(spi, xtb1_cs, baudrate=10000000, drdy=xtb1_DRDY, refV=VREF)
time.sleep(1)
# make sure the board is alive
if xtb1.regreadout()[0] != 8:
    # neopixel_write.neopixel_write(neopix, bytearray([0,255,0]))
    while True:
        time.sleep(2)

save_time = time.monotonic()
save_int = 5 # time in seconds between saving to the SD card

payload = []
flag = False
while True:
    now = time.monotonic()
    # XTB BASELINE MEASUREMENT
    # data = xtb1.test(inp=8, inn=12, ref=AVDD, printout=True)

    # HALL MEASUREMENT
    # make 100 voltage measurements as quickly as possible between AIN1 and AIN2, while driving a current of 250uA on AIN3, and biasing AIN0 at 0.275V
    data = xtb1.readpins(inp=8, inn=12, idacMux=15, idacMag=0x04, vb=0, pga=0x00, ref=AVDD, datarate=0x1B, burst=300)
    payload.append((now,data))

    if now >= save_time:
        neopixel_write.neopixel_write(neopix, bytearray([0,0,255]))
        save_time = now + save_int
        # make a temperature measurement
        temperature = xtb1.readtemp(ref=AVDD)
        try:
            path = '/sd/'+filename    
            with open(path, "a") as f:
                print('saving to...',path)
                for item in payload:
                    f.write('{}, {}, '.format(temperature,item[0]))
                    for i in item[1]:
                        f.write('{:E}, '.format(i))
                    f.write('\n')
                    # f.flush()
                    # f.close()
                payload = []
        except Exception as e:
            print('--- SD card error ---')
            print(e)
            sdcard = False
            neopixel_write.neopixel_write(neopix, bytearray([0,255,0]))
            while True:
                time.sleep(2)
        neopixel_write.neopixel_write(neopix, bytearray([0,0,0]))
        gc.collect()