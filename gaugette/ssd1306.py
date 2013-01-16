#----------------------------------------------------------------------
# ssd1306.py from https://github.com/guyc/py-gaugette
# ported by Guy Carpenter, Clearwater Software
#
# This library is for the Adafruit 128x32 SPI monochrome OLED 
# based on the SSD1306 driver.
#   http://www.adafruit.com/products/661
#
# This library does not directly support the larger 128x64 module,
# but could with minor changes.
#
# The code is based heavily on Adafruit's Arduino library
#   https://github.com/adafruit/Adafruit_SSD1306
# written by Limor Fried/Ladyada for Adafruit Industries.
#
# The datasheet for the SSD1306 is available
#   http://www.adafruit.com/datasheets/SSD1306.pdf
#
# WiringPi pinout reference
#   https://projects.drogon.net/raspberry-pi/wiringpi/pins/
#
# Some important things to know about this device and SPI:
#
# - The SPI interface has no MISO connection.  It is write-only.
#
# - The spidev xfer and xfer2 calls overwrite the output buffer
#   with the bytes read back in during the SPI transfer.
#   Use writebytes instead of xfer to avoid having your buffer overwritten.
#
# - The D/C (Data/Command) line is used to distinguish data writes
#   and command writes - HIGH for data, LOW for commands.  To be clear,
#   the attribute bytes following a command opcode are NOT considered data,
#   data in this case refers only to the display memory buffer.
#   keep D/C LOW for the command byte including any following argument bytes.
#   Pull D/C HIGH only when writting to the display memory buffer.
#   
# - The pin connections between the Raspberry Pi and OLED module are:
#
#      RPi     SSD1306
#      CE0   -> CS
#      GPIO2 -> RST   (to use a different GPIO set reset_pin to wiringPi pin no)
#      GPIO1 -> D/C   (to use a different GPIO set dc_pin to wiringPi pin no)
#      SCLK  -> CLK
#      MOSI  -> DATA
#      3.3V  -> VIN
#            -> 3.3Vo
#      GND   -> GND
#----------------------------------------------------------------------

import spidev
import wiringpi
import time
import font5x8
import sys

class SSD1306:

    # Class constants are externally accessible as gaugette.ssd1306.SSD1306.CONST
    # or my_instance.CONST

    # TODO - insert underscores to rationalize constant names

    EXTERNAL_VCC   = 0x1
    SWITCH_CAP_VCC = 0x2
        
    SET_LOW_COLUMN        = 0x00
    SET_HIGH_COLUMN       = 0x10
    SET_MEMORY_MODE       = 0x20
    SET_COL_ADDRESS       = 0x21
    SET_PAGE_ADDRESS      = 0x22
    RIGHT_HORIZ_SCROLL    = 0x26
    LEFT_HORIZ_SCROLL     = 0x27
    VERT_AND_RIGHT_HORIZ_SCROLL = 0x29
    VERT_AND_LEFT_HORIZ_SCROLL = 0x2A
    DEACTIVATE_SCROLL     = 0x2E
    ACTIVATE_SCROLL       = 0x2F
    SET_START_LINE        = 0x40
    SET_CONTRAST          = 0x81
    CHARGE_PUMP           = 0x8D
    SEG_REMAP             = 0xA0
    SET_VERT_SCROLL_AREA  = 0xA3
    DISPLAY_ALL_ON_RESUME = 0xA4
    DISPLAY_ALL_ON        = 0xA5
    NORMAL_DISPLAY        = 0xA6
    INVERT_DISPLAY        = 0xA7
    DISPLAY_OFF           = 0xAE
    DISPLAY_ON            = 0xAF
    COM_SCAN_INC          = 0xC0
    COM_SCAN_DEC          = 0xC8
    SET_DISPLAY_OFFSET    = 0xD3
    SET_COM_PINS          = 0xDA
    SET_VCOM_DETECT       = 0xDB
    SET_DISPLAY_CLOCK_DIV = 0xD5
    SET_PRECHARGE         = 0xD9
    SET_MULTIPLEX         = 0xA8

    MEMORY_MODE_HORIZ = 0x00
    MEMORY_MODE_VERT  = 0x01
    MEMORY_MODE_PAGE  = 0x02

    # Device name will be /dev/spidev-{bus}.{device}
    # dc_pin is the data/commmand pin.  This line is HIGH for data, LOW for command.
    # We will keep d/c low and bump it high only for commands with data
    # reset is normally HIGH, and pulled LOW to reset the display

    def __init__(self, bus=0, device=0, dc_pin=1, reset_pin=2, buffer_rows=64, buffer_cols=128):
        self.cols = 128
        self.rows = 32
        self.buffer_rows = 64
        self.mem_bytes = self.buffer_rows * self.cols / 8 # total bytes in SSD1306 display ram
        self.dc_pin = dc_pin
        self.reset_pin = reset_pin
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 500000
        self.gpio = wiringpi.GPIO(wiringpi.GPIO.WPI_MODE_PINS)
        self.gpio.pinMode(self.reset_pin, self.gpio.OUTPUT)
        self.gpio.digitalWrite(self.reset_pin, self.gpio.HIGH)
        self.gpio.pinMode(self.dc_pin, self.gpio.OUTPUT)
        self.gpio.digitalWrite(self.dc_pin, self.gpio.LOW)
        self.font = font5x8.Font5x8
        self.col_offset = 0
        self.bitmap = self.Bitmap(buffer_cols, buffer_rows)
        self.flipped = False

    def reset(self):
        self.gpio.digitalWrite(self.reset_pin, self.gpio.LOW)
        self.gpio.delay(10) # 10ms
        self.gpio.digitalWrite(self.reset_pin, self.gpio.HIGH)

    def command(self, *bytes):
        # already low
        # self.gpio.digitalWrite(self.dc_pin, self.gpio.LOW) 
        self.spi.writebytes(list(bytes))

    def data(self, bytes):
        self.gpio.digitalWrite(self.dc_pin, self.gpio.HIGH)
        self.spi.writebytes(bytes)
        self.gpio.digitalWrite(self.dc_pin, self.gpio.LOW)
        
    def begin(self, vcc_state = SWITCH_CAP_VCC):
        self.gpio.delay(1) # 1ms
        self.reset()
        self.command(self.DISPLAY_OFF)
        self.command(self.SET_DISPLAY_CLOCK_DIV, 0x80)
        self.command(self.SET_MULTIPLEX, 0x1F)
        self.command(self.SET_DISPLAY_OFFSET, 0x00)
        self.command(self.SET_START_LINE | 0x00)
        if (vcc_state == self.EXTERNAL_VCC):
            self.command(self.CHARGE_PUMP, 0x10)
        else:
            self.command(self.CHARGE_PUMP, 0x14)
        self.command(self.SET_MEMORY_MODE, 0x00)
        self.command(self.SEG_REMAP | 0x01)
        self.command(self.COM_SCAN_DEC)
        self.command(self.SET_COM_PINS, 0x02)
        self.command(self.SET_CONTRAST, 0x8f)
        if (vcc_state == self.EXTERNAL_VCC):
            self.command(self.SET_PRECHARGE, 0x22)
        else:
            self.command(self.SET_PRECHARGE, 0xF1)
        self.command(self.SET_VCOM_DETECT, 0x40)
        self.command(self.DISPLAY_ALL_ON_RESUME)
        self.command(self.NORMAL_DISPLAY)
        self.command(self.DISPLAY_ON)
        
    def clear_display(self):
    	self.bitmap.clear()

    def invert_display(self):
        self.command(self.INVERT_DISPLAY)

    def flip_display(self, flipped=True):
        self.flipped = flipped
        if flipped:
            self.command(self.COM_SCAN_INC)
            self.command(self.SEG_REMAP | 0x00)
        else:
            self.command(self.COM_SCAN_DEC)
            self.command(self.SET_COM_PINS, 0x02)

    def normal_display(self):
        self.command(self.NORMAL_DISPLAY)

    def set_contrast(self, contrast=0x7f):
        self.command(self.SET_CONTRAST, contrast)

    def display(self):
    	self.display_block(self.bitmap, 0, 0, self.cols)

    def display_cols(self, start_col, count):
        self.display_block(self.bitmap, 0, start_col, count)

    # Transfers data from the passed bitmap (instance of ssd1306.Bitmap)
    # starting at row <row> col <col>.
    # Both row and bitmap.rows will be divided by 8 to get page addresses,
    # so both must divide evenly by 8 to avoid surprises.
    #
    # bitmap:     instance of Bitmap
    #             The number of rows in the bitmap must be a multiple of 8.
    # row:        Starting row to write to - must be multiple of 8
    # col:        Starting col to write to.
    # col_count:  Number of cols to write.
    # col_offset: column offset in buffer to write from
    #  
    def display_block(self, bitmap, row, col, col_count, col_offset=0):
        page_count = bitmap.rows >> 3
        page_start = row >> 3
        page_end   = page_start + page_count - 1
        col_start  = col
        col_end    = col + col_count - 1
        self.command(self.SET_MEMORY_MODE, self.MEMORY_MODE_VERT)
        self.command(self.SET_PAGE_ADDRESS, page_start, page_end)
        self.command(self.SET_COL_ADDRESS, col_start, col_end)
        start = col_offset * page_count
        length = col_count * page_count
        self.data(bitmap.data[start:start+length])

    # Diagnostic print of the memory buffer to stdout 
    def dump_buffer(self):
        self.bitmap.dump()

    def draw_pixel(self, x, y, on=True):
        self.bitmap.draw_pixel(x,y,on)
        
    def draw_text(self, x, y, string):
        font_bytes = self.font.bytes
        font_rows = self.font.rows
        font_cols = self.font.cols
        for c in string:
            p = ord(c) * font_cols
            for col in range(0,font_cols):
                mask = font_bytes[p]
                p+=1
                for row in range(0,8):
                    self.draw_pixel(x,y+row,mask & 0x1)
                    mask >>= 1
                x += 1

    def draw_text2(self, x, y, string, size=2, space=1):
        font_bytes = self.font.bytes
        font_rows = self.font.rows
        font_cols = self.font.cols
        for c in string:
            p = ord(c) * font_cols
            for col in range(0,font_cols):
                mask = font_bytes[p]
                p+=1
                py = y
                for row in range(0,8):
                    for sy in range(0,size):
                        px = x
                        for sx in range(0,size):
                            self.draw_pixel(px,py,mask & 0x1)
                            px += 1
                        py += 1
                    mask >>= 1
                x += size
            x += space

    def clear_block(self, x0,y0,dx,dy):
        self.bitmap.clear_block(x0,y0,dx,dy)
        
    def draw_text3(self, x, y, string, font):
        self.bitmap.draw_text(x,y,string,font)

    class Bitmap:
    
        # Pixels are stored in column-major order!
        # This makes it easy to reference a vertical slice of the display buffer
        # and we use the to achieve reasonable performance vertical scrolling 
        # without hardware support.
        def __init__(self, cols, rows):
            self.rows = rows
            self.cols = cols
            self.bytes_per_col = rows / 8
            self.data = [0] * (self.cols * self.bytes_per_col)
    
        def clear(self):
	    for i in range(0,len(self.data)):
            	self.data[i] = 0

        # Diagnostic print of the memory buffer to stdout 
        def dump(self):
            for y in range(0, self.rows):
                mem_row = y/8
                bit_mask = 1 << (y % 8)
                line = ""
                for x in range(0, self.cols):
                    mem_col = x
                    offset = mem_row + self.rows/8 * mem_col
                    if self.data[offset] & bit_mask:
                        line += '*'
                    else:
                        line += ' '
                print('|'+line+'|')
                
        def draw_pixel(self, x, y, on=True):
            if (x<0 or x>=self.cols or y<0 or y>=self.rows):
                return
            mem_col = x
            mem_row = y / 8
            bit_mask = 1 << (y % 8)
            offset = mem_row + self.rows/8 * mem_col
    
            if on:
                self.data[offset] |= bit_mask
            else:
                self.data[offset] &= (0xFF - bit_mask)
    
        def clear_block(self, x0,y0,dx,dy):
            for x in range(x0,x0+dx):
                for y in range(y0,y0+dy):
                    self.draw_pixel(x,y,0)
              
        def draw_text(self, x, y, string, font):
            height = font.char_height
            prev_char = None
    
            for c in string:
                if (c<font.start_char or c>font.end_char):
                    if prev_char != None:
                        x += font.space_width + prev_width + font.gap_width
                    prev_char = None
                else:
                    pos = ord(c) - ord(font.start_char)
                    (width,offset) = font.descriptors[pos]
    
                    if prev_char != None:
                        x += font.kerning[prev_char][pos] + font.gap_width
                        
                    prev_char = pos
                    prev_width = width
                    
                    bytes_per_row = (width + 7) / 8
                    for row in range(0,height):
                        py = y + row
                        mask = 0x80
                        p = offset
                        for col in range(0,width):
                            px = x + col
                            if (font.bitmaps[p] & mask):
                                self.draw_pixel(px,py,1)  # for kerning, never draw black
                            mask >>= 1
                            if mask == 0:
                                mask = 0x80
                                p+=1
                        offset += bytes_per_row
              
            if prev_char != None:
                x += prev_width
    
            return x

    # This is a helper class to display a scrollable list of text lines.
    # The list must have at least 1 item.
    class ScrollingList:
        def __init__(self, ssd1306, list, font):
            self.ssd1306 = ssd1306
            self.list = list
            self.font = font
            self.position = 0 # row index into list, 0 to len(list) * self.rows - 1
            self.offset = 0   # led hardware scroll offset
            self.pan_row = -1
            self.pan_offset = 0
            self.pan_direction = 1
            self.bitmaps = []
            self.rows = ssd1306.rows
            self.cols = ssd1306.cols
            self.bufrows = self.rows * 2
            downset = (self.rows - font.char_height)/2
            for text in list:
                width = ssd1306.cols
                text_bitmap = ssd1306.Bitmap(width, self.rows)
                width = text_bitmap.draw_text(0,downset,text,font)
                if width > 128:
                    text_bitmap = ssd1306.Bitmap(width+15, self.rows)
                    text_bitmap.draw_text(0,downset,text,font)
                self.bitmaps.append(text_bitmap)
                
            # display the first word in the first position
            self.ssd1306.display_block(self.bitmaps[0], 0, 0, self.cols)
    
        # how many steps to the nearest home position
        def home_offset(self):
            pos = self.position % self.rows
            delta = (pos + 15) % self.rows - 15
            return delta
    
        # scroll up or down.  Does multiple one-pixel scrolls if delta is not >1 or <-1
        def scroll(self, delta):
            if delta == 0:
                return
    
            count = len(self.list)
            step = cmp(delta, 0)
            for i in range(0,delta, step):
                if (self.position % self.rows) == 0:
                    n = self.position / self.rows
                    # at even boundary, need to update hidden row
                    m = (n + step + count) % count
                    row = (self.offset + self.rows) % self.bufrows
                    self.ssd1306.display_block(self.bitmaps[m], row, 0, self.cols)
                    if m == self.pan_row:
                        self.pan_offset = 0
                self.offset = (self.offset + self.bufrows + step) % self.bufrows
                self.ssd1306.command(self.ssd1306.SET_START_LINE | self.offset)
                max_position = count * self.rows
                self.position = (self.position + max_position + step) % max_position
    
        # pans the current row back and forth repeatedly.
        # Note that this currently only works if we are at a home position.
        def auto_pan(self):
            n = self.position / self.rows
            if n != self.pan_row:
                self.pan_row = n
                self.pan_offset = 0
                
            text_bitmap = self.bitmaps[n]
            if text_bitmap.cols > self.cols:
                row = self.offset # this only works if we are at a home position
                if self.pan_direction > 0:
                    if self.pan_offset <= (text_bitmap.cols - self.cols):
                        self.pan_offset += 1
                    else:
                        self.pan_direction = -1
                else:
                    if self.pan_offset > 0:
                        self.pan_offset -= 1
                    else:
                        self.pan_direction = 1
                self.ssd1306.display_block(text_bitmap, row, 0, self.cols, self.pan_offset)
    
