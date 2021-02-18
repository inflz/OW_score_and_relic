# Various classes and variables for the tracker to make use of

# DESOLATION FACILITY PROFILE (dynamic zone ID)
# facility_names = {400284: 'Relic Atma', 400285: 'Relic Bane', 400287: 'Relic Chiron', 400288: 'Relic Deimos',
#                   400289: 'Relic Etna', 400290: 'Relic Feros', 400291: 'Relic Gamma', 400292: 'Relic Hosk',
#                   400293: 'Relic Ibri'}  # Static region IDs and their corresponding facility name

# AMERISH TEST FACILITY PROFILE (zone 6)
facility_names = {217000: 'Relic Atma', 222350: 'Relic Bane', 222180: 'Relic Chiron', 222150: 'Relic Deimos',
                  222280: 'Relic Etna', 222270: 'Relic Feros', 208001: 'Relic Gamma', 208000: 'Relic Hosk',
                  222190: 'Relic Ibri'}

# ESAMIR TEST FACILITY PROFILE (zone 8)
# facility_names = {246000: 'Relic Atma', 254000: 'Relic Bane', 248000: 'Relic Chiron', 244100: 'Relic Deimos',
#                   244610: 'Relic Etna', 249000: 'Relic Feros', 400314: 'Relic Gamma', 400135: 'Relic Hosk',
#                   234000: 'Relic Ibri'}

MAX_SCORE = 750


class RelicFacility:
    """Manages and stores score data for a relic in an OW match"""
    def __init__(self, facility_id: int, zone_id: int):
        """Initializes variables for each facility"""
        self.facility_id = facility_id  # Static region id
        self.zone_id = zone_id   # Dynamic zone id (in the event that multiple matches must be tracked simultaneously)
        self.name = None
        self.letter = None
        self.time_vs_approx = 0  # Approximated time (s) each faction has owned relic, incremented when inc() is called
        self.time_nc_approx = 0
        self.time_tr_approx = 0
        self.time_vs_actual = 0  # Actual RPG server time (s) each faction has owned relic, updated every territory flip
        self.time_nc_actual = 0
        self.time_tr_actual = 0
        self.score_vs = 0  # Score produced with this relic for each faction
        self.score_nc = 0
        self.score_tr = 0
        self.current_faction = 0  # Faction based on ID; 1 is VS, 2 is NC, 3 is TR
        for facility in facility_names:  # Set name based on facility ID
            if facility == id:
                self.name = facility_names[facility]
                self.letter = self.name[6:7]
                break

    def inc(self):
        """Increments one second to approximate time for current territory owner"""
        if self.current_faction == 1:  # Increment VS
            self.time_vs_approx += 1
        elif self.current_faction == 2:  # Increment NC
            self.time_nc_approx += 1
        elif self.current_faction == 3:  # Increment TR
            self.time_tr_approx += 1

    def calculate_region_score(self):
        """Calculates the score for every faction based on approximate time"""
        self.score_vs = self.time_vs_approx // 10  # Calculates 1 point for every 10 seconds of ownership
        self.score_nc = self.time_nc_approx // 10
        self.score_tr = self.time_tr_approx // 10

    def recalibrate_time_vs(self, latest_duration_held):
        """Adjusts approximate time VS have held the base based on confirmed server time. Recalculates region score."""
        self.time_vs_actual += latest_duration_held
        self.time_vs_approx = self.time_vs_actual
        self.calculate_region_score()

    def recalibrate_time_nc(self, latest_duration_held):
        """Adjusts approximate time NC have held the base based on confirmed server time. Recalculates region score."""
        self.time_nc_actual += latest_duration_held
        self.time_nc_approx = self.time_nc_actual
        self.calculate_region_score()

    def recalibrate_time_tr(self, latest_duration_held):
        """Adjusts approximate time TR have held the base based on confirmed server time. Recalculates region score."""
        self.time_tr_actual += latest_duration_held
        self.time_tr_approx = self.time_tr_actual
        self.calculate_region_score()


class OWMatch:
    """Manages and stores score data for an entire OW match"""
    def __init__(self, zone_id: int, match_name: str = None):
        """Initializes variables for each match"""
        self.zone_id = zone_id  # Dyanmic zone ID of desolation instance match takes place on
        self.match_name = match_name  # Optional name of match for the tracker to use
        self.total_score_vs = 0  # Calculated scores for all three factions
        self.total_score_nc = 0
        self.total_score_tr = 0
        self.relics = []  # Stores data on relics and their individual scores/ownership
        self.scoring = True  # Determines whether scoring is currently enabled
        self.winner = None
        for facility in facility_names:  # Adds all 9 relics to match
            self.relics.append(RelicFacility(facility, zone_id))

    def inc_relics(self):
        """Adds one approximate second of ownership to all relic timers for applicable factions (if any). Should be run
        exactly once every second or for an equivalent amount of the mythical RPG server time."""
        if self.scoring:
            for relic in self.relics:
                relic.inc()  # Inc function handles whether or not faction should be incremented

    def flip_relic(self, facility_id: int, prev_faction_id: int, new_faction_id: int, latest_duration_held: int):
        """Changes faction of relic that was flipped and recalibrates region time"""
        if prev_faction_id != new_faction_id:  # Ensure that event is not a defense which does not reset time
            for relic in self.relics:
                if relic.facility_id == facility_id:
                    relic.current_faction = new_faction_id  # Changes relic faction
                    if prev_faction_id == 1:  # Recalibrates if VS previous owner
                        relic.recalibrate_time_vs(latest_duration_held)
                    elif prev_faction_id == 2:  # Recalibrates if NC previous owner
                        relic.recalibrate_time_nc(latest_duration_held)
                    elif prev_faction_id == 3:  # Recalibrates if TR previous owner
                        relic.recalibrate_time_tr(latest_duration_held)
                    break

    def update_scores(self):
        """Updates total scores for all three factions based on individual relic scores. Can be run as often as it is
        desired for scores to be refreshed (recommended at >2s intervals). Also stops tracking and determines winner if
        score goes above maximum required to win."""
        temp_score_vs = 0  # Sets temporary score that can be incremented for each relic and then transferred to total
        temp_score_nc = 0
        temp_score_tr = 0
        for relic in self.relics:  # Calculate, then add score for each relic to temp var
            relic.calculate_region_score()
            temp_score_vs += relic.score_vs
            temp_score_nc += relic.score_nc
            temp_score_tr += relic.score_tr
        self.total_score_vs = temp_score_vs  # Update match score values
        self.total_score_nc = temp_score_nc
        self.total_score_tr = temp_score_tr
        if self.total_score_vs >= MAX_SCORE:
            self.total_score_vs = 750
            self.stop_scoring()
            self.winner = 1
        elif self.total_score_nc >= MAX_SCORE:
            self.total_score_nc = 750
            self.stop_scoring()
            self.winner = 2
        elif self.total_score_tr >= MAX_SCORE:
            self.total_score_tr = 750
            self.stop_scoring()
            self.winner = 3

    def stop_scoring(self):
        """Forces all relics in match to stop counting score by changing territory status to unclaimed (intended to be
        used at conclusion of match)."""
        self.scoring = False
        for relic in self.relics:
            relic.current_faction = 0


if __name__ == '__main__':  # Debug/testing area
    print('This module (utils.py) should not be run on its own unless you are debugging.')
