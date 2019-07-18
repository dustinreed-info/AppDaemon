
import appdaemon.plugins.hass.hassapi as hass
import datetime
import time
import pytz
tz = pytz.timezone('America/Chicago')
class Light(hass.Hass):
    def initialize(self):
        '''
        Pulls arguments from apps.yaml and sets variables.
        Listens to light events based upon time.
        '''
        #Sets flag if not already set.  flag is used to ensure the light stays off if it is in the middle of fade_in().
        try:
            if self.flag == None:
                self.flag = 0
        except: 
            self.flag = 0
        #Pulls arguments from apps.yaml 
        try:
            self.light = self.args['name']
            self.time = self.args['time']
            self.start = self.args['start']
            self.end = self.args['end']
            self.step = self.args['step']
            self.delay = self.args['delay']
            #Listens to light events and will turn on or fade in depending on the time.
            self.listen_event(self.fade_in, event=self.args['lighton'],
                constrain_start_time=self.time['start'], constrain_end_time=self.time['end'], new = 'on' )
            self.listen_event(self.light_on, event=self.args['lighton'], 
                constrain_start_time= self.time['end'], constrain_end_time=self.time['start'], new = 'on' )
            self.listen_event(self.light_off, event=self.args['lightoff'], new = 'on')
            self.run_hourly(self.light_schedule,datetime.time(22,00,00))
        except:
            self.log('Sensor')

    def get_color_temp(self):
        try:
            return self.color_temp
        #If color temp not set, then set to warmest temperature bulbs can handle.
        except:
            self.color_temp = 490
            return self.color_temp

    def get_start(self):
        return self.start

    def light_schedule(self, *args):
        '''
        Sets a light schedule that adjusted the lights color temperature and brightness
        depending on the time.
        '''
        if self.light[0:5] == 'light':
            self.log(self.light)
            self.log('Adjusting Kelvin Schedule')
            dt = datetime.datetime.now().hour
            if dt < 3:
                #kelvin = 2700
                self.color_temp = 370
                self.brightness = 50 
            elif dt >= 3 and dt < 7:
                #kelvin = 2000
                self.brightness = 10 
                self.color_temp = 490
            elif dt >= 7 and dt < 20:
                #kelvin = 5000
                self.brightness = 255
                self.color_temp = 153
            else:
                #kelvin = 3700
                self.color_temp = 270
                self.brightness = 128
            if self.get_state(self.light) == 'on':
                self.light_on(self.light, self.brightness, self.color_temp)
            
    def fade_in(self, *args):
        '''
        Increases lights brightness and changes color temperature from warm to cool.
        Values are pulled from apps.yaml
        - step is the rate of change multiplier
        - delay increases the delay between step
        '''
        self.log(f'fade_in: {self.light} starting brightness: {self.get_start()}')
        self.flag = 0
        start = self.get_start()
        end = self.brightness
        delay = self.delay
        step = self.step
        target_temp = self.get_color_temp()
        self.color_temp = 490

        def step_counter(self, start, step, target_temp, *args):            
            start += step
            if target_temp < self.color_temp:
                # Adjust step multiplier if you want color temperature change rate.
                self.color_temp = self.color_temp - step * 2.5
            return start

        while start <= end and self.flag == 0:
            self.light_on(self.light, start,self.get_color_temp())
            start = step_counter(self, start, step, target_temp, self.get_color_temp())
            if self.flag == 1:
                break
        time.sleep(delay)
        self.log('broke free from fade in') 
        self.terminate()

    def fade_out(self, *args):
        '''
        Decreases lights brightness and changes color temperature from warm to cool.
        Values are pulled from apps.yaml
        - step is the rate of change multiplier
        - delay increases the delay between step
        '''
        self.flag = 0
        name = self.light
        start = self.get_start()
        end = self.end
        delay = self.delay
        step = self.step
        while end >= start and self.flag == 0:
            self.log(start)
            self.light_on(name, end, self.color_temp)
            # Adjust step multiplier if you want to adjust rate of change for brightness or color temp.
            end -= step * 5
            self.color_temp -= step
            if self.flag == 1:
                break
        
        time.sleep(delay)
        self.flag = 1
        self.light_on(name, start,self.color_temp)
        self.turn_off(self.light)


        
    def light_on (self, name, start, color_temp):
        '''
        Checks to see if a light has a set brightness and turns on light.  If it does not have a set
        brightness it runs the light_schedule function to obtain one.
        '''
        if start == {}:
            self.log('start empty')
            try:
                color_temp = self.color_temp
                start = self.brightness
            except:
                self.log('color temp or brightness not set')
                self.turn_on(self.light)
                self.light_schedule()
        #self.log(self.get_state(self.light))
        if self.get_state(name) == 'off':
            self.log(f'light_on: {name}')
        self.turn_on(self.light, brightness = start, color_temp = self.get_color_temp(), effect = 0)
        time.sleep(self.delay)
    def light_off(self, *args):
        self.log(f'light_off: {self.light}')
        self.flag = 1
        self.brightness = self.get_state(self.light, attribute='brightness')
        self.color_temp = self.get_state(self.light, attribute='color_temp')
        self.turn_off(self.light)

    def terminate(self):
        '''
        If self.flag is On then will turn light off and log that the terminate function was used.
        '''
        if self.flag == 1:
            self.turn_off(self.light)
            self.log("light term")
        self.log('terminated')

class MotionLight(hass.Hass):
    '''
    Turns on motion light when the time is within 1 hour of sun rise or sun set and motion is detected.
    '''
    def initialize(self):
        self.sensor = self.args['sensor']
        self.switch = self.args['switch']
        dt = datetime.datetime.now().time().hour
        self.listen_state(self.motion, self.sensor, new = "on")
        self.listen_state(self.motion_off, self.sensor, new = "off", duration = 180)
    def motion(self, entity, attribute, old, new, kwargs):
        dt = datetime.datetime.now().time().hour
        if dt < self.sunrise().time().hour + 1 or self.sunset().time().hour - 1  <= dt:
            self.log(f'{self.switch}: on!')
            self.turn_on(self.switch)
    def motion_off(self, *args):
        self.log(f'{self.switch}: off!')
        self.turn_off(self.switch)
