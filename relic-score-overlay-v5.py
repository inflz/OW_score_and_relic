import obspython as obs
import requests
import json
import random
import threading
import datetime

world = '1'
target_zone = '0'
service_id = '17034223270'

rate_update_interval = 3

api_update_interval = 5

text_update_interval = 3

scoreboard_source_names = dict()

previous_relic_status = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0, 'G': 0, 'H': 0, 'I': 0}
previous_wg_status = {'N_WG': 0, 'SE_WG': 0, 'SW_WG': 0}
previous_connected_status = {'A': True, 'B': True, 'C': True, 'D': True, 'E': True, 'F': True, 'G': True, 'H': True,
                             'I': True}

first_time = True

rate_vs = '0 pt/min'
rate_nc = '0 pt/min'
rate_tr = '0 pt/min'

status_codes = {400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found', 408: 'Request Timeout',
                500: 'Internal Server Error', 502: 'Bad Gateway', 503: 'Service Unavailable', 504: 'Gateway Timeout'}

# DESOLATION VALUES
region_names = {18221: 'Atma', 18222: 'Bane', 18224: 'Chiron', 18225: 'Deimos', 18226: 'Etna', 18227: 'Feros',
                18228: 'Gamma', 18229: 'Hosk', 18230: 'Ibri'}

# AMERISH TEST (zone 6)
# region_names = {6205: 'Atma', 6316: 'Bane', 6351: 'Chiron', 6112: 'Deimos', 6307: 'Etna', 6328: 'Feros',
#                 6319: 'Gamma', 6335: 'Hosk', 6329: 'Ibri'}

# ESAMIR TEST (zone 8)
# region_names = {18210: 'Atma', 18067: 'Bane', 18005: 'Chiron', 18019: 'Deimos', 18032: 'Etna', 18020: 'Feros',
#                 18250: 'Gamma', 18017: 'Hosk', 18025: 'Ibri'}

server_ids = {'Connery': '1', 'Miller': '10', 'Cobalt': '13', 'Emerald': '17', 'Jaeger': '19', 'Apex': '24',
              'Soltech': '40'}

relic_source_names = ['A_VS', 'A_NC', 'A_TR', 'B_VS', 'B_NC', 'B_TR', 'C_VS', 'C_NC', 'C_TR', 'D_VS', 'D_NC', 'D_TR',
                     'E_VS', 'E_NC', 'E_TR', 'F_VS', 'F_NC', 'F_TR', 'G_VS', 'G_NC', 'G_TR', 'H_VS', 'H_NC', 'H_TR',
                     'I_VS', 'I_NC', 'I_TR']

# DESOLATION VALUES
warpgate_names = {18215: 'N_WG', 18216: 'SW_WG', 18217: 'SE_WG'}

# ESAMIR TEST (ZONE 8)
# warpgate_names = {18029: 'N_WG', 18030: 'SW_WG', 18062: 'SE_WG'}

desolation_facility_lattice_connections = {'N_WG': ['A', 'B'], 'SW_WG': ['E', 'F'], 'SE_WG': ['C', 'D'],
                                           'A': ['F', 'G', 'N_WG'], 'B': ['H', 'C', 'N_WG'], 'C': ['B', 'H', 'SE_WG'],
                                           'D': ['I', 'E', 'SE_WG'], 'E': ['I', 'D', 'SW_WG'], 'F': ['A', 'G', 'SW_WG'],
                                           'G': ['A', 'F', 'H', 'I'], 'H': ['B', 'C', 'G', 'I'],
                                           'I': ['E', 'D', 'G', 'H']}
start_pressed = False


class RelicFacility:
    """Stores data for a relic in an OW match"""
    def __init__(self, region_id: int, zone_id: int):
        """Initializes variables for each facility"""
        self.region_id = region_id  # Static region id
        self.zone_id = zone_id   # Dynamic zone id (in the event that multiple matches must be tracked simultaneously)
        self.current_faction = 0  # Faction based on ID; 1 is VS, 2 is NC, 3 is TR
        self.connected = True
        for region in region_names:  # Set name based on facility ID
            if region == region_id:
                self.name = 'Relic '+region_names[region]
                self.letter = self.name[6:7]
                break


class OWMatch:
    """Manages and stores score data for an entire OW match"""
    def __init__(self, zone_id: int, match_name: str = None):
        """Initializes variables for each match"""
        self.zone_id = zone_id  # Dyanmic zone ID of desolation instance match takes place on
        self.match_name = match_name  # Optional name of match for the tracker to use
        self.warpgate_nc = None
        self.warpgate_vs = None
        self.warpgate_tr = None
        self.relics = []  # Stores data on relics and their individual scores/ownership
        for region in region_names:  # Adds all 9 relics to match
            self.relics.append(RelicFacility(region, zone_id))

    def is_connected(self, relic_letter: str, warpgate: str, relic_letters_owned: list):
        """Recursive function that scans lattices to see if specified relic is connected to the warpgate. If used,
        must handle RecursionError exception."""

        global desolation_facility_lattice_connections

        if relic_letter in relic_letters_owned:
            if warpgate in desolation_facility_lattice_connections[relic_letter]:
                return True
            conn_list = desolation_facility_lattice_connections[relic_letter]
            for connection in random.sample(conn_list, len(conn_list)):
                if self.is_connected(connection, warpgate, relic_letters_owned):
                    return True
            return False
        else:
            return False

    def validate_relic_lattice_connections(self):
        """Disconnects relics from scoring that become cut off from their faction's warpgate."""
        if (self.warpgate_vs is not None) and (self.warpgate_nc is not None) and (self.warpgate_tr is not None):
            vs_owned = []
            nc_owned = []
            tr_owned = []

            for relic in self.relics:  # Populate list of currently owned relics
                if relic.current_faction == 1:
                    vs_owned.append(relic.letter)
                elif relic.current_faction == 2:
                    nc_owned.append(relic.letter)
                elif relic.current_faction == 3:
                    tr_owned.append(relic.letter)

            for relic in vs_owned:
                if relic is not None:
                    try:
                        if self.is_connected(relic, self.warpgate_vs, vs_owned):
                            for outer_relic in self.relics:
                                if outer_relic.letter == relic:
                                    outer_relic.connected = True
                                    break
                        else:
                            for outer_relic in self.relics:
                                if outer_relic.letter == relic:
                                    outer_relic.connected = False
                                    break
                    except RecursionError:
                        for outer_relic in self.relics:
                            if outer_relic.letter == relic:
                                outer_relic.connected = False
                                break
                    except Exception as excptn:
                        print(f'[{datetime.datetime.now()}][TRACKER] EXCEPTION DETECTED: ', excptn.__class__.__name__)
                        print(f'[{datetime.datetime.now()}][TRACKER] Attempted to pass:', relic, self.warpgate_vs, vs_owned)
                        print(f'[{datetime.datetime.now()}][TRACKER]', type(relic), type(self.warpgate_vs), type(vs_owned))

            for relic in nc_owned:
                if relic is not None:
                    try:
                        if self.is_connected(relic, self.warpgate_nc, nc_owned):
                            for outer_relic in self.relics:
                                if outer_relic.letter == relic:
                                    outer_relic.connected = True
                                    break
                        else:
                            for outer_relic in self.relics:
                                if outer_relic.letter == relic:
                                    outer_relic.connected = False
                                    break
                    except RecursionError:
                        for outer_relic in self.relics:
                            if outer_relic.letter == relic:
                                outer_relic.connected = False
                                break
                    except Exception as excptn:
                        print(f'[{datetime.datetime.now()}][TRACKER] EXCEPTION DETECTED ', excptn.__class__.__name__)
                        print(f'[{datetime.datetime.now()}][TRACKER] Attempted to pass', relic, self.warpgate_nc, nc_owned)
                        print(f'[{datetime.datetime.now()}][TRACKER]', type(relic), type(self.warpgate_nc), type(nc_owned))

            for relic in tr_owned:
                if relic is not None:
                    try:
                        if self.is_connected(relic, self.warpgate_tr, tr_owned):
                            for outer_relic in self.relics:
                                if outer_relic.letter == relic:
                                    outer_relic.connected = True
                                    break
                        else:
                            for outer_relic in self.relics:
                                if outer_relic.letter == relic:
                                    outer_relic.connected = False
                                    break
                    except RecursionError:
                        for outer_relic in self.relics:
                            if outer_relic.letter == relic:
                                outer_relic.connected = False
                                break
                    except Exception as excptn:
                        print(f'[{datetime.datetime.now()}][TRACKER] EXCEPTION DETECTED ', excptn.__class__.__name__)
                        print(f'[{datetime.datetime.now()}][TRACKER] Attempted to pass', relic, self.warpgate_tr, tr_owned)
                        print(f'[{datetime.datetime.now()}][TRACKER]', type(relic), type(self.warpgate_tr), type(tr_owned))


def update_territory_data(match: OWMatch):
    """Sends web request to Census API and updates status of territories based on response."""

    global service_id, world, target_zone, previous_relic_status, previous_wg_status, previous_connected_status, \
        first_time

    if not first_time:
        for relic in match.relics:  # Get previous state of relics prior to update
            try:
                previous_relic_status[relic.letter] = relic.current_faction
            except KeyError:
                print(f'[{datetime.datetime.now()}][TRACKER] ERROR: Failed to set relic letter due to KeyError, Line 196.')

        url = f'https://census.daybreakgames.com/s:{service_id}/get/ps2:v2/map/?world_id={world}&zone_ids={target_zone}'

        print(f'[{datetime.datetime.now()}][WEB REQUEST] Querying API...')  # Get new relic data from API
        try:
            response = requests.get(url)
            if response.status_code == 200:  # Success
                print(f'[{datetime.datetime.now()}][WEB REQUEST] 200 OK')
            elif response.status_code == 429:  # Rate limit
                print(f'[{datetime.datetime.now()}][WEB REQUEST] ERROR 429: TOO MANY REQUESTS! Stopping tracker. Slow down update rate and try again.')
            elif response.status_code in status_codes:  # Specific error
                print(f'[{datetime.datetime.now()}][WEB REQUEST] ERROR {response.status_code}: {status_codes[response.status_code]}')
            else:  # Generic error
                print(f'[{datetime.datetime.now()}][WEB REQUEST] UNEXPECTED RESPONSE: {response.status_code}')

            try:
                payload = json.loads(response.text)  # Load json payload
                try:
                    territory_list = payload['map_list'][0]['Regions']['Row']
                    for territory in territory_list:
                        region_id = int(territory['RowData']['RegionId'])
                        faction_id = int(territory['RowData']['FactionId'])
                        for relic in match.relics:  # Update faction IDs of relics
                            if relic.region_id == region_id:
                                relic.current_faction = faction_id
                                break

                        if (match.warpgate_vs == None) or (match.warpgate_nc == None) or (match.warpgate_tr == None):
                            for warpgate_id in warpgate_names:  # Update warpgate IDs
                                if warpgate_id == region_id:
                                    if faction_id == 1:
                                        match.warpgate_vs = warpgate_names.get(warpgate_id, None)
                                    elif faction_id == 2:
                                        match.warpgate_nc = warpgate_names.get(warpgate_id, None)
                                    elif faction_id == 3:
                                        match.warpgate_tr = warpgate_names.get(warpgate_id, None)
                except KeyError:
                    print(f'[{datetime.datetime.now()}][WEB REQUEST] ERROR: Failed to parse json data from response. Printing response.')
                    print(response.text)
            except Exception as e:
                print(f'[{datetime.datetime.now()}][WEB REQUEST] ERROR: Failed to load json data from response. Printing response.')
                print(f'[{datetime.datetime.now()}][WEB REQUEST]', response.text)

            match.validate_relic_lattice_connections()
            print(f'[{datetime.datetime.now()}][TRACKER] Successfully validated facility lattice connections.')

            for relic in match.relics:  # Change relic factions on UI
                for prev_status in previous_relic_status.keys():
                    if prev_status == relic.letter:  # Find letter of relic in recorded list
                        if previous_relic_status[prev_status] != relic.current_faction:
                            print(f'[{datetime.datetime.now()}][TRACKER] Detected territory change in Relic '+relic.letter)
                            prev_source_names = []
                            source_name_current = None
                            current_letter = relic.letter

                            if current_letter is not None:
                                if relic.current_faction == 1:
                                    source_name_current = current_letter + '_VS'
                                    prev_source_names = [current_letter + '_NC', current_letter + '_TR']
                                elif relic.current_faction == 2:
                                    source_name_current = current_letter + '_NC'
                                    prev_source_names = [current_letter + '_VS', current_letter + '_TR']
                                elif relic.current_faction == 3:
                                    source_name_current = current_letter + '_TR'
                                    prev_source_names = [current_letter + '_NC', current_letter + '_VS']
                                elif relic.current_faction == 0 or relic.current_faction == 4:
                                    source_name_current = None
                                    prev_source_names = [current_letter + '_VS', current_letter + '_NC', current_letter + '_TR']

                            if len(prev_source_names) > 0:
                                for source_name_prev in prev_source_names:
                                    prev_source = obs.obs_get_source_by_name(source_name_prev)
                                    if prev_source is not None:
                                        obs.obs_source_set_enabled(prev_source, False)
                                    obs.obs_source_release(prev_source)

                            if source_name_current is not None:
                                current_source = obs.obs_get_source_by_name(source_name_current)
                                if current_source is not None:
                                    obs.obs_source_set_enabled(current_source, True)
                                obs.obs_source_release(current_source)

                            previous_relic_status[prev_status] = relic.current_faction
                            # update this relic
                        break

            for relic in match.relics:  # Change relic cutoff status on UI
                if relic.connected != previous_connected_status[relic.letter]:  # Change in cutoff status
                    source_name_current = None
                    current_letter = relic.letter
                    if current_letter is not None:
                        source_name_current = current_letter + '_cutoff'
                    if relic.connected:
                        if current_letter is not None:
                            current_source = obs.obs_get_source_by_name(source_name_current)
                            if current_source is not None:
                                obs.obs_source_set_enabled(current_source, False)
                            obs.obs_source_release(current_source)
                    else:
                        if current_letter is not None:
                            current_source = obs.obs_get_source_by_name(source_name_current)
                            if current_source is not None:
                                obs.obs_source_set_enabled(current_source, True)
                            obs.obs_source_release(current_source)
                    previous_connected_status[relic.letter] = relic.connected

            for wg in warpgate_names:  # Change warpgate factions on UI
                source_name_current = None
                source_name_others = None
                if match.warpgate_vs is not None:
                    if warpgate_names[wg] == match.warpgate_vs:
                        if previous_wg_status[match.warpgate_vs] != 1:
                            source_name_current = match.warpgate_vs+'_VS'
                            source_name_others = [match.warpgate_vs+'_NC', match.warpgate_vs+'_TR']
                            if source_name_others is not None:
                                for source_name_otr in source_name_others:
                                    prev_source = obs.obs_get_source_by_name(source_name_otr)
                                    if prev_source is not None:
                                        obs.obs_source_set_enabled(prev_source, False)
                                    obs.obs_source_release(prev_source)
                            if source_name_current is not None:
                                current_source = obs.obs_get_source_by_name(source_name_current)
                                if current_source is not None:
                                    obs.obs_source_set_enabled(current_source, True)
                                obs.obs_source_release(current_source)
                            previous_wg_status[match.warpgate_vs] = 1
                if match.warpgate_nc is not None:
                    if warpgate_names[wg] == match.warpgate_nc:
                        if previous_wg_status[match.warpgate_nc] != 2:
                            source_name_current = match.warpgate_nc+'_NC'
                            source_name_others = [match.warpgate_nc + '_VS', match.warpgate_nc + '_TR']
                            if source_name_others is not None:
                                for source_name_otr in source_name_others:
                                    prev_source = obs.obs_get_source_by_name(source_name_otr)
                                    if prev_source is not None:
                                        obs.obs_source_set_enabled(prev_source, False)
                                    obs.obs_source_release(prev_source)
                            if source_name_current is not None:
                                current_source = obs.obs_get_source_by_name(source_name_current)
                                if current_source is not None:
                                    obs.obs_source_set_enabled(current_source, True)
                                obs.obs_source_release(current_source)
                            previous_wg_status[match.warpgate_nc] = 2
                if match.warpgate_tr is not None:
                    if warpgate_names[wg] == match.warpgate_tr:
                        if previous_wg_status[match.warpgate_tr] != 3:
                            source_name_current = match.warpgate_tr + '_TR'
                            source_name_others = [match.warpgate_tr + '_VS', match.warpgate_tr + '_NC']
                            if source_name_others is not None:
                                for source_name_otr in source_name_others:
                                    prev_source = obs.obs_get_source_by_name(source_name_otr)
                                    if prev_source is not None:
                                        obs.obs_source_set_enabled(prev_source, False)
                                    obs.obs_source_release(prev_source)
                            if source_name_current is not None:
                                current_source = obs.obs_get_source_by_name(source_name_current)
                                if current_source is not None:
                                    obs.obs_source_set_enabled(current_source, True)
                                obs.obs_source_release(current_source)
                            previous_wg_status[match.warpgate_tr] = 3

            print(f'[{datetime.datetime.now()}][TRACKER] Successfully updated relic sources.')
        except Exception as conn_err:
            print(f'[{datetime.datetime.now()}][WEB REQUEST] Error:', conn_err.__class__.__name__)
    first_time = False


def start_rate_update(match: OWMatch):
    """Starts thread loop for rate update"""

    global rate_vs, rate_nc, rate_tr, rate_update_thread

    rate_update_thread = threading.Timer(rate_update_interval, start_rate_update, args=[match])
    rate_update_thread.start()

    vs_relics_connected = 0
    nc_relics_connected = 0
    tr_relics_connected = 0

    for relic in match.relics:  # Check how many relics each faction owns
        if relic.current_faction == 1 and relic.connected:
            vs_relics_connected += 1
        elif relic.current_faction == 2 and relic.connected:
            nc_relics_connected += 1
        elif relic.current_faction == 3 and relic.connected:
            tr_relics_connected += 1

    rate_vs = str(vs_relics_connected*6)+' pt/min'  # Update faction point gain rate
    rate_nc = str(nc_relics_connected*6)+' pt/min'
    rate_tr = str(tr_relics_connected*6)+' pt/min'


def start_api_update(match: OWMatch):
    """Starts thread loop for API territory data update"""

    global api_update_thread

    api_update_thread = threading.Timer(api_update_interval, start_api_update, args=[match])
    api_update_thread.start()

    update_territory_data(match)


def start_tracker(props, prop):
    """Starts necessary threads for tracking matches."""

    global start_pressed, current_match, target_zone

    if not start_pressed:
        start_pressed = True
        obs.script_log(obs.LOG_INFO, f'[{datetime.datetime.now()}][TRACKER] \'Start Tracker\' button pressed, '
                                     f'initializing websocket and tracker.')

        current_match = OWMatch(int(target_zone))

        obs.script_log(obs.LOG_INFO, f'[{datetime.datetime.now()}][TRACKER] Starting rate data update thread.')
        start_rate_update(current_match)

        obs.script_log(obs.LOG_INFO, f'[{datetime.datetime.now()}][TRACKER] Starting API data update thread.')
        start_api_update(current_match)
    else:
        obs.script_log(obs.LOG_WARNING, f'[{datetime.datetime.now()}][TRACKER] \'Start Tracker\' button was pressed '
                                        f'after tracker already started. No action was performed.')


def stop_tracker(props, prop):
    """Closes tracking threads and websocket connection."""

    global start_pressed, api_update_thread, rate_update_thread

    if start_pressed:
        start_pressed = False
        obs.script_log(obs.LOG_INFO, f'[{datetime.datetime.now()}][TRACKER] \'Stop Tracker\' button pressed, shutting '
                                     f'down tracker.')
        api_update_thread.cancel()
        rate_update_thread.cancel()
        obs.script_log(obs.LOG_INFO, f'[{datetime.datetime.now()}][TRACKER] Tracking threads closed.')
    else:
        obs.script_log(obs.LOG_WARNING, f'[{datetime.datetime.now()}][TRACKER] \'Stop Tracker\' button pressed '
                                        f'without starting the tracker first. No action was performed.')


def reset_relics(props, prop):
    """Sets faction of all relics in overlay to NS by disabling overlays for other factions"""

    global previous_relic_status, previous_wg_status, previous_connected_status

    for name in relic_source_names:  # Iterate through and disable relic overlay sources
        source = obs.obs_get_source_by_name(name)
        if source is not None:
            obs.obs_source_set_enabled(source, False)
        obs.obs_source_release(source)  # Release sources to prevent memory leak

    for name in warpgate_names:  # Iterate through and disable warpgate overlay sources
        for fxn in ['_VS', '_NC', '_TR']:
            nm = warpgate_names[name]+fxn
            source = obs.obs_get_source_by_name(nm)
            if source is not None:
                obs.obs_source_set_enabled(source, False)
            obs.obs_source_release(source)  # Release sources to prevent memory leak

    for name in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']:  # Iterate through and disable cutoff overlay sources
        nm = name+'_cutoff'
        source = obs.obs_get_source_by_name(nm)
        if source is not None:
            obs.obs_source_set_enabled(source, False)
        obs.obs_source_release(source)  # Release sources to prevent memory leak

    previous_relic_status = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0, 'G': 0, 'H': 0, 'I': 0}
    previous_wg_status = {'N_WG': 0, 'SE_WG': 0, 'SW_WG': 0}
    previous_connected_status = {'A': True, 'B': True, 'C': True, 'D': True, 'E': True, 'F': True, 'G': True, 'H': True,
                                 'I': True}


def update_text():
    """Updates text sources for the scoreboard"""

    global scoreboard_source_names, rate_vs, rate_nc, rate_tr

    scoreboard_source_names['RATE_VS'] = rate_vs
    scoreboard_source_names['RATE_NC'] = rate_nc
    scoreboard_source_names['RATE_TR'] = rate_tr

    for name in scoreboard_source_names:  # Iterate through list and update sources in OBS
        source = obs.obs_get_source_by_name(name)
        if source is not None:
            try:
                settings = obs.obs_data_create()
                obs.obs_data_set_string(settings, "text", scoreboard_source_names[name])
                obs.obs_source_update(source, settings)
                obs.obs_data_release(settings)
            except:
                obs.script_log(obs.LOG_WARNING, f'[{datetime.datetime.now()}][TRACKER] Encountered error updating '
                                                f'scoreboard source')
                obs.remove_current_callback()

        obs.obs_source_release(source)  # Releases source and prevents memory leak


def script_description():
    """Description displayed on script configuration panel."""

    return "Updates scoreboard and relic status. Must be used alongside the provided source groups. You should " \
           "only modify the position/visibility of the source group, do not change any individual sources or it may " \
           "break. When start tracker is pressed, the script opens a HTTP connection to the PS2 API and tracks " \
           "relics based on the provided parameters. If you want a detailed log of what the tracker is doing, " \
           "open the script log.\n" \
           "\nInstructions for use:" \
           "\n1. Once on desolation, obtain six digit desolation zone ID using /zone." \
           "\n2. Prior to match, select server and enter desolation ID in fields below." \
           "\n3. Press \'Start Tracker\' at any time during prep phase or the match." \
           "\n4. Press \'Stop Tracker\' after the match has concluded." \
           "\n5. Feel free to press \'Reset Relics\' before or after a match to set territory back to neutral."


def script_update(settings):
    """Called every time the script updates."""

    global world, target_zone

    target_zone = str(obs.obs_data_get_int(settings, "target_zone"))
    try:
        world = server_ids[obs.obs_data_get_string(settings, "world")]
    except KeyError:
        print('[TRACKER] Attempted to fetch world but server ID not set')

    obs.timer_remove(update_text)
    obs.timer_add(update_text, text_update_interval * 1000)


def script_defaults(settings):
    """Sets default valu4es for script properties"""

    obs.obs_data_set_default_string(settings, "world", "Connery")
    obs.obs_data_set_default_int(settings, "target_zone", 0)


def script_properties():
    """Adds elements to script configuration panel"""

    props = obs.obs_properties_create()

    serv_l = obs.obs_properties_add_list(props, "world", "Server", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(serv_l, "Connery", "Connery")  # Server list
    obs.obs_property_list_add_string(serv_l, "Miller", "Miller")
    obs.obs_property_list_add_string(serv_l, "Cobalt", "Cobalt")
    obs.obs_property_list_add_string(serv_l, "Emerald", "Emerald")
    obs.obs_property_list_add_string(serv_l, "Jaeger", "Jaeger")
    obs.obs_property_list_add_string(serv_l, "Apex", "Apex")
    obs.obs_property_list_add_string(serv_l, "Soltech", "Soltech")

    obs.obs_properties_add_int(props, "target_zone", "Desolation Instance Zone ID", 0, 999999, 1)

    obs.obs_properties_add_button(props, "button2", "Start Tracker", start_tracker)  # Buttons
    obs.obs_properties_add_button(props, "button3", "Stop Tracker", stop_tracker)
    obs.obs_properties_add_button(props, "button", "Reset Relics", reset_relics)

    return props
