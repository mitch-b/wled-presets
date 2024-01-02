# Home Assistant Configuration

I have an automation with my WLED controller to automate holiday-specific presets/playlists based on the day. 

To facilitate this automation, I also have some Helpers and a HACS integration to keep things clean.

```yaml
alias: Holiday Roof Lights 🏠
description: ""
trigger:
  - platform: sun
    event: sunset
    offset: 0
    id: sunset
  - platform: sun
    event: sunset
    offset: "00:00:10"
    id: sunset2
  - platform: time
    at: "01:00:00"
    id: 1am
  - platform: time
    at: "05:00:00"
    id: 5am
  - platform: sun
    event: sunrise
    offset: "00:05:00"
    id: sunrise+5
condition: []
action:
  - alias: Set playlist for holiday
    choose:
      - conditions:
          - condition: trigger
            id:
              - 1am
              - sunrise+5
        sequence:
          - type: turn_off
            device_id: d6fd614f7f05cb3e140649a69e9ee387
            entity_id: abf05a1e5576c5dfe0c2969fb616d822
            domain: light
          - type: turn_off
            device_id: d6fd614f7f05cb3e140649a69e9ee387
            entity_id: 5a63fc497bd1e525910dcf4aa889a300
            domain: light
        alias: Turn off
      - conditions:
          - condition: state
            entity_id: binary_sensor.independence_day_holiday
            state: "on"
        sequence: []
        alias: July 4th
      - conditions:
          - condition: state
            entity_id: binary_sensor.halloween_holiday
            state: "on"
        sequence: []
        alias: Halloween
      - conditions:
          - condition: state
            entity_id: binary_sensor.thanksgiving_holiday
            state: "on"
        sequence: []
        alias: Thanksgiving
      - conditions:
          - condition: state
            entity_id: binary_sensor.christmas_holiday
            state: "on"
        sequence:
          - device_id: d6fd614f7f05cb3e140649a69e9ee387
            domain: select
            entity_id: 528ff2c552505fcb97aa33042d5ebb63
            type: select_option
            option: Christmas
        alias: Christmas 🎄
      - conditions:
          - condition: state
            entity_id: binary_sensor.new_years_holiday
            state: "on"
        sequence:
          - device_id: d6fd614f7f05cb3e140649a69e9ee387
            domain: select
            entity_id: db302cb55cae6341bf37220a3e902634
            type: select_option
            option: NYE Fireworks (Split)
        alias: New Years (Eve+Day)
    default:
      - stop: No matching Holiday sensor
mode: single
```

## HACS Integration: next_holiday

...

## Helpers

...
