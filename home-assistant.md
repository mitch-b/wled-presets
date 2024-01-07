# Home Assistant Configuration

I have an automation with my WLED controller to automate holiday-specific presets/playlists based on the day.

To facilitate this automation, I also have some Helpers and a HACS integration to keep things clean.

I have some triggers repeated with small offsets, that's a hacky way to try the command twice if the first fails silently. 

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

GitHub: [partofthething/next-holiday-sensor](https://github.com/partofthething/next-holiday-sensor)

As a part of 2024.01 Home Assistant, an official `holiday` integration was added. I was going to switch, but the benefit of this custom approach is that I can also add in Halloween, and family birthdays that I also would want to trigger holiday-specific automations.

## Helpers

### Independence Day

`binary_sensor.independence_day_holiday`

```yaml
{{ 
   states('sensor.next_holiday') == 'Independence Day'
   and 
   state_attr('sensor.next_holiday','days_until_next_holiday') == 0
}}
```

### Halloween

`binary_sensor.halloween_holiday`

```yaml
{{ 
   states('sensor.next_holiday') == 'Halloween'
   and 
   state_attr('sensor.next_holiday','days_until_next_holiday') == 0
}}
```

### Thanksgiving

`binary_sensor.thanksgiving_holiday`

```yaml
{{ 
   states('sensor.next_holiday') == 'Thanksgiving' 
   and 
   state_attr('sensor.next_holiday','days_until_next_holiday') == 0
}}
```

### Christmas Holiday 

`binary_sensor.christmas_holiday`

```yaml
{{ 
  (
    states('sensor.next_holiday') == 'Christmas Day' 
    and 
    state_attr('sensor.next_holiday','days_until_next_holiday') < 35
  ) 
  
  or
  
  states('sensor.next_holiday') == 'Christmas Day (Observed)'
  
  or
  
  (
    states('sensor.next_holiday') == 'New Year\'s Day'
    and 
    state_attr('sensor.next_holiday','days_until_next_holiday') > 1
  )
  
  or
   
  states('sensor.next_holiday') == 'New Year\'s Day (Observed)')

  or
   
  states('sensor.next_holiday') == 'Martin Luther King Jr. Day'
}}
```

### New Year's Holiday

`binary_sensor.new_years_holiday`

```yaml
{{ 
  (
    states('sensor.next_holiday') == 'New Year\'s Day'
    and 
    state_attr('sensor.next_holiday','days_until_next_holiday') <= 1
  )
  
  or

  states('sensor.next_holiday') == 'New Year\'s Day (Observed)'
}}
```
