
import math

class range_est():

    def __init__(self, battery_capacity, dist_avg, time_avg, n_runs, roll_energy, roll_distance):
        self.max_battery = battery_capacity                         # kWh, useable energy (58 kWh for Stargazer)
        self.dist_avg = dist_avg                                    # kWh/nm, updated and stored after each run
        self.time_avg = time_avg                                    # kWh/min, updated and stored after each run
        self.n_runs = n_runs                                        # int, # trips that contribute to efficiency; zero this to reset
        self.range_remaining = 0                                    # nm
        self.time_remaining = 0                                     # min
        
        ## used only for rolling avg
        self.n_mins = 10                                            # interval for updating rolling average reference points
        self.roll_energy = roll_energy                              # last energy useage, overwritten every n_mins
        self.roll_distance = roll_distance                          # last distance traveled, overwritten every n_mins
        self.roll_consumption = 0                                   # efficiency value updated every n_mins
        self.roll_avg = 0                                           # weighted efficiency that combines roll_consumption and dist_avg


    def tick(self, data):
        """This function allows the UW team to change which algorithm is being used without altering the nmea2000 server script."""
        self.overall_avg(data)


    def overall_avg(self, data):
        """This function evaluates range and time remaining on the battery given historical consumption data."""
        self.range_remaining = data['energyAvailable']/self.dist_avg        # nm
        self.time_remaining = data['energyAvailable']/self.time_avg         # min 


    def overall_time_avg(self, data):
        """This function evaluates time remaining on the battery given historical time consumption data (kWh/min)
        and then multiplies it by the average trip speed to attain range remaining."""
        self.time_remaining = data['energyAvailable']/self.time_avg         # min 
        trip_speed = data['tripDistance']/data['tripDuration']*3600         # kts
        self.range_remaining = (self.time_remaining/60)*trip_speed          # nm


    def rolling_avg(self, data):
        """This function evaluates range remaining on the battery by incorporating more recent consumption history.
        Every n_mins a new reference point is created with roll_energy and roll_distance, which is then used to
        calculate the rolling consumption rate. A fractional scale is applied to blend the rolling consumption with
        the stored distance consumption to slowly give more weight to recent trip history."""

        ## Update rolling consumption rate every n_mins and reset stored values
        if (data['tripDuration']/60) % self.n_mins == 0:
            curr_roll_energy = data['energyUsed'] - self.roll_energy
            curr_roll_distance = data['tripDistance'] - self.roll_distance
            self.roll_consumption = curr_roll_energy/curr_roll_distance
            self.roll_energy = data['energyUsed']
            self.roll_distance = data['tripDistance']

        t = 0
        weight = 0

        ## default to stored overall average if n_mins have not surpassed yet, otherwise blend in rolling average
        if (data['tripDuration']/60) <= self.n_mins:
            self.roll_avg = self.dist_avg
        elif (data['tripDuration']/60) > self.n_mins:
            t = (data['tripDuration']/60) - self.n_mins
            # weight = math.log(self.data['tripDuration'])
            weight = t/(t+self.n_mins)
            self.roll_avg = ((1-weight)*self.dist_avg) + (weight*self.roll_consumption)

        self.range_remaining = data['energyAvailable']/self.roll_avg


    def update_avg(self, data):
        """This function should be called whenever a trip is completed. It updates the cached averages for both
        time and distance, and stores the average efficiencies as well as the number of runs it is averaged over.

        NOTE: The commented code below is another method for incorporating the new trip average. Instead of
        averaging over all n_runs, it weights the new trip average at 15% every time the function is run."""


        self.n_runs += 1
        # alpha = 0.15

        ### Calculate the trip distance average and incorporate into the stored overall average
        trip_dist_avg = data['energyUsed']/data['tripDistance']
        new_dist_avg = (self.n_runs*self.dist_avg + trip_dist_avg)/(self.n_runs)        
        self.dist_avg = new_dist_avg                                                # kWh/nm
        # self.dist_avg = ((1-alpha)*self.dist_avg) + (alpha*dist_avg)

        ### Calculate the trip time average and incorporate into the stored overall average
        trip_time_avg = data['energyUsed']/data['tripDuration']*60
        new_time_avg = (self.n_runs*self.time_avg + trip_time_avg)/(self.n_runs)
        self.time_avg = new_time_avg                                                # kWh/min
        # self.time_avg = ((1-alpha)*self.time_avg) + (alpha*time_avg)
