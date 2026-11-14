# Home Assistant Configuration

I have an automation with my WLED controller to automate holiday-specific presets/playlists based on the day.

This is an example of one setup, not a drop-in configuration. The device IDs, entity IDs, and select options in the automation are specific to my Home Assistant and WLED setup. Replace them with the IDs and options from your own instance, and make sure the helper entity IDs match the ones referenced by your automation.

The automation runs at sunset and retries 10 seconds later, as well as at 1:00 AM, 5:00 AM, and five minutes after sunrise. The 1:00 AM and sunrise triggers turn the lights off. For other triggers, the `choose` action runs only the first matching branch, so branch order matters. The July 4th, Halloween, and Thanksgiving branches currently have empty sequences and do not select a preset. The default action stops the automation when none of the holiday helpers is on.

The WLED select options (for example, `Christmas`) must already be available on the selected entity in your setup.

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

## HACS custom integration: Next Holiday Sensor

Project: [partofthething/next-holiday-sensor](https://github.com/partofthething/next-holiday-sensor)

The custom integration provides `sensor.next_holiday`: its state is the next holiday's name (or that day's holiday when today is a holiday), and its `days_until_next_holiday` attribute is used by the templates below. Follow the project's README for HACS installation and sensor configuration; it documents configuring a country/region source and adding recurring dates with `custom_holidays` (such as Halloween or family birthdays). This guide assumes the sensor is already installed, configured, and has the entity ID and attribute shown above.

Home Assistant's built-in [Holiday integration](https://www.home-assistant.io/integrations/holiday/) provides a calendar of public holidays for a country and optional region. It is an alternative for public-holiday calendars, but it does not expose the `sensor.next_holiday` state and `days_until_next_holiday` attribute these templates expect, so switching to it requires adapting the helpers.

## Helpers

Create these as Template binary sensor helpers in **Settings > Devices & services > Helpers > Create helper > Template**. Use the template for each helper as its state template, and make sure its resulting entity ID matches the one listed here. The names returned by `sensor.next_holiday` must also match the strings in the templates (including punctuation and localization).

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

This helper selects the Christmas theme during the month before Christmas, on Christmas Day (including an observed date), and through the New Year's/early-January holiday period shown below. The `New Year's Day (Observed)` case also turns on the New Year's helper; because the Christmas branch comes first in the automation, Christmas takes precedence on that date.

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
   
  states('sensor.next_holiday') == 'New Year\'s Day (Observed)'

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
