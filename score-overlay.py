import obspython as obs
import json, utils, threading, websocket

interval = 5
update_interval = 5
source_name = ''
start_pressed = False

score_vs = '0'
score_nc = '0'
score_tr = '0'
tag_vs = '[TAG]'
tag_nc = '[TAG]'
tag_tr = '[TAG]'
rate_vs = '0 pt/min'
rate_nc = '0 pt/min'
rate_tr = '0 pt/min'
source_list = dict()
relic_source_list = ['A_VS', 'A_NC', 'A_TR', 'B_VS', 'B_NC', 'B_TR', 'C_VS', 'C_NC', 'C_TR', 'D_VS', 'D_NC', 'D_TR',
                     'E_VS', 'E_NC', 'E_TR', 'F_VS', 'F_NC', 'F_TR', 'G_VS', 'G_NC', 'G_TR', 'H_VS', 'H_NC', 'H_TR',
                     'I_VS', 'I_NC', 'I_TR']
target_zone = ''
world = ''


# TRACKER FUNCTIONS ----------------------------------------------------------------------------------------------------
def process_payload(payload: str):
    json_payload = json.loads(payload)
    if 'payload' in json_payload.keys():
        facility_id = int(json_payload['payload']['facility_id'])
        if (json_payload['payload']['zone_id'] == target_zone) and (facility_id in utils.facility_names.keys()):
            faction_id_current = int(json_payload['payload']['new_faction_id'])
            faction_id_prev = int(json_payload['payload']['old_faction_id'])
            if faction_id_prev != faction_id_current:
                source_name_current = None
                source_name_prev = None
                print('[WEBSOCKET] BASE FLIPPED! DURATION HELD -', json_payload['payload']['duration_held'], 's')
                testmatch.flip_relic(facility_id, faction_id_prev, faction_id_current, int(json_payload['payload']['duration_held']))
                letter = utils.facility_names[facility_id][6:7]
                print(letter)
                print(type(letter))

                if faction_id_current == 1:
                    print('got 1 faction')
                    source_name_current = letter+'_VS'
                elif faction_id_current == 2:
                    print('got 1 faction')
                    source_name_current = letter+'_NC'
                elif faction_id_current == 3:
                    print('got 1 faction')
                    source_name_current = letter+'_TR'
                if faction_id_prev == 1:
                    print('got 1 faction')
                    source_name_prev = letter+'_VS'
                elif faction_id_prev == 2:
                    print('got 1 faction')
                    source_name_prev = letter+'_NC'
                elif faction_id_prev == 3:
                    print('got 1 faction')
                    source_name_prev = letter+'_TR'

                prev_source = obs.obs_get_source_by_name(source_name_prev)
                if prev_source is not None:
                    print('enabling previous source'+source_name_prev)
                    obs.obs_source_set_enabled(prev_source, False)
                obs.obs_source_release(prev_source)

                current_source = obs.obs_get_source_by_name(source_name_current)
                if current_source is not None:
                    obs.obs_source_set_enabled(current_source, True)
                obs.obs_source_release(current_source)

def on_ws_message(ws, message):
    print(f'[WEBSOCKET] PAYLOAD: {message}')
    process_payload(str(message))


def on_ws_close(ws):
    print('[WEBSOCKET] CONNECTION CLOSED')


def on_ws_error(ws, error):
    print('[WEBSOCKET]', error)


def on_ws_open(ws):
    print('[WEBSOCKET] Connection open')
    ws.send(f'{{"service":"event","action":"subscribe","eventNames":["{event_name}"],"worlds":[{world}]}}')


def start_timer(match: utils.OWMatch):
    threading.Timer(increment_interval, start_timer, args=[match]).start()
    match.inc_relics()


def start_update_loop(match: utils.OWMatch):
    global score_vs
    global score_nc
    global score_tr
    global rate_vs
    global rate_nc
    global rate_tr
    vs_relics_owned = 0
    nc_relics_owned = 0
    tr_relics_owned = 0

    threading.Timer(update_interval, start_update_loop, args=[match]).start()
    match.update_scores()
    print('[SCORE UPDATE]', 'VS', match.total_score_vs, '-', 'NC', match.total_score_nc, '-', 'TR', match.total_score_tr)

    score_vs = str(match.total_score_vs)  # Update faction scores
    score_nc = str(match.total_score_nc)
    score_tr = str(match.total_score_tr)

    for relic in match.relics:  # Check how many relics each faction owns
        if relic.current_faction == 1:
            vs_relics_owned += 1
        elif relic.current_faction == 2:
            nc_relics_owned += 1
        elif relic.current_faction == 3:
            tr_relics_owned += 1

    rate_vs = str(vs_relics_owned*6)+' pt/min'  # Update faction point gain rate
    rate_nc = str(nc_relics_owned*6)+' pt/min'
    rate_tr = str(tr_relics_owned*6)+' pt/min'


def start_tracker(props, prop):
    global start_pressed
    global testmatch
    global increment_interval
    global event_name
    global ws
    global wst
    if not start_pressed:
        start_pressed = True
        obs.script_log(obs.LOG_INFO, '[OBS] Start Tracker button pressed')
        uri = "wss://push.planetside2.com/streaming?environment=ps2&service-id=s:17034223270"
        testmatch = utils.OWMatch(int(target_zone))
        increment_interval = 1
        event_name = 'FacilityControl'

        websocket.enableTrace(True)
        ws = websocket.WebSocketApp(uri, on_message=on_ws_message, on_close=on_ws_close, on_error=on_ws_error,
                                    on_open=on_ws_open)
        obs.script_log(obs.LOG_INFO, '[WEBSOCKET] Starting thread')
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()

        obs.script_log(obs.LOG_INFO, '[TIMER] Starting thread')
        start_timer(testmatch)

        obs.script_log(obs.LOG_INFO, '[SCORE UPDATE] Starting thread')
        start_update_loop(testmatch)


def stop_tracker(props, prop):
    global start_pressed
    global ws
    if start_pressed:
        obs.script_log(obs.LOG_INFO, '[OBS] Stop tracker button pressed')
        ws.send('{"service":"event","action":"clearSubscribe","all":"true"}')
        ws.close()
        wst.join()
        start_pressed = False


def reset_relics(props, prop):
    for name in relic_source_list:
        source = obs.obs_get_source_by_name(name)
        if source is not None:
            obs.obs_source_set_enabled(source, False)
        obs.obs_source_release(source)


# OBS FUNCTIONS --------------------------------------------------------------------------------------------------------
def update_text():
    global source_list
    global score_vs
    global score_nc
    global score_tr
    global tag_vs
    global tag_nc
    global tag_tr
    global rate_vs
    global rate_nc
    global rate_tr

    source_list['SCORE_VS'] = score_vs  # Update list of source names and values
    source_list['SCORE_NC'] = score_nc
    source_list['SCORE_TR'] = score_tr
    source_list['TAG_VS'] = tag_vs
    source_list['TAG_NC'] = tag_nc
    source_list['TAG_TR'] = tag_tr
    source_list['RATE_VS'] = rate_vs
    source_list['RATE_NC'] = rate_nc
    source_list['RATE_TR'] = rate_tr

    for name in source_list:  # Iterate through list and update sources in OBS
        source = obs.obs_get_source_by_name(name)
        if source is not None:
            try:
                settings = obs.obs_data_create()
                obs.obs_data_set_string(settings, "text", source_list[name])
                obs.obs_source_update(source, settings)
                obs.obs_data_release(settings)
            except:
                obs.script_log(obs.LOG_WARNING, 'ERROR UPDATING SOURCE')
                obs.remove_current_callback()

        obs.obs_source_release(source)  # Releases source and prevents memory leak


def script_description():
    return "Updates scoreboard with score. Must be used alongside the provided scoreboard source group. You should " \
           "only modify the position/visibility of the source group, do not change any individual sources or it may " \
           "break. When start tracker is pressed, the script opens a websocket connection to the PS2 API and tracks " \
           "score based on the provided parameters. If you want a detailed log of what the tracker is doing and the " \
           "websocket information received, open the script log.\n" \
           "\nInstructions for use:" \
           "\n1. Prior to match, enter desolation ID, server ID, and outfit tags." \
           "\n2. Start the tracker any time before the first territory is captured in a match." \
           "3. Do not stop the tracker until after the match has concluded or it will fall out of sync."

def script_update(settings):
    global interval
    global update_interval
    global target_zone
    global world
    global tag_vs
    global tag_nc
    global tag_tr

    interval = obs.obs_data_get_int(settings, "interval")
    world = str(obs.obs_data_get_int(settings, "world"))
    target_zone = str(obs.obs_data_get_int(settings, "target_zone"))
    update_interval = obs.obs_data_get_int(settings, "update_interval")

    tag_vs = obs.obs_data_get_string(settings, "tag_vs")
    tag_nc = obs.obs_data_get_string(settings, "tag_nc")
    tag_tr = obs.obs_data_get_string(settings, "tag_tr")

    obs.timer_remove(update_text)
    obs.timer_add(update_text, interval * 1000)


def script_defaults(settings):
    obs.obs_data_set_default_int(settings, "interval", 5)
    obs.obs_data_set_default_int(settings, "update_interval", 5)
    obs.obs_data_set_default_int(settings, "target_zone", 6)
    obs.obs_data_set_default_int(settings, "world", 17)
    obs.obs_data_set_default_string(settings, "tag_vs", "[TAG]")
    obs.obs_data_set_default_string(settings, "tag_nc", "[TAG]")
    obs.obs_data_set_default_string(settings, "tag_tr", "[TAG]")


def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_int_slider(props, "interval", "OBS Textbox Update Interval (s)", 3, 60, 1)
    obs.obs_properties_add_int_slider(props, "update_interval", "Tracker Score Calculation Interval (s)", 3, 60, 1)
    obs.obs_properties_add_int(props, "target_zone", "Desolation Instance Zone ID", 0, 999999, 1)
    obs.obs_properties_add_int(props, "world", "Server (World) ID", 0, 999, 1)
    obs.obs_properties_add_text(props, "tag_vs", "VS Outfit Tag", obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_properties_add_text(props, "tag_nc", "NC Outfit Tag", obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_properties_add_text(props, "tag_tr", "TR Outfit Tag", obs.OBS_COMBO_FORMAT_STRING)

    #p = obs.obs_properties_add_list(props, "source", "Text Source", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    #sources = obs.obs_enum_sources()
    #if sources is not None:
    #    for source in sources:
    #        source_id = obs.obs_source_get_unversioned_id(source)
    #        if source_id == "text_gdiplus" or source_id == "text_ft2_source":
    #            name = obs.obs_source_get_name(source)
    #            obs.obs_property_list_add_string(p, name, name)
    #
    #    obs.source_list_release(sources)

    obs.obs_properties_add_button(props, "button2", "Start Tracker", start_tracker)
    obs.obs_properties_add_button(props, "button3", "Stop Tracker", stop_tracker)
    obs.obs_properties_add_button(props, "button", "Reset Relics", reset_relics)
    return props