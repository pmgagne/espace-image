# Product Context — Espace-Image

## Problem Statement

### The Challenge

Families have hundreds/thousands of digital photos collecting dust in cloud storage or phone galleries. Traditional digital picture frames are expensive, limited, and lack smart features like calendar integration. iPads/tablets sitting unused could serve this purpose, but no simple solution exists that:

1. Works reliably on old hardware (iPad 2 from 2011)
2. Integrates calendar alarms for family scheduling
3. Shows weather without opening separate apps
4. Requires zero technical maintenance

### User Pain Points

- **Photo Overload**: Photos never get displayed, only stored
- **Calendar Chaos**: Family events scattered across devices, easy to forget
- **Old Hardware**: iPad 2 too slow for modern apps, but too good to throw away
- **Complexity**: Commercial solutions require subscriptions, cloud accounts, complex setup
- **Privacy**: Don't want family photos on third-party cloud services

## Solution

**Espace-Image** transforms any tablet into an intelligent digital picture frame with three core features:

1. **Rotating Photo Slideshow**: Upload photos via web interface, group into presets, automatic rotation
2. **Calendar Alarms**: Pop-up notifications for family events synced from iCloud/Google Calendar
3. **Weather Display**: Live weather widget for daily planning

**Special Capability**: Full support for iPad 2 (iOS 9.3.5) via legacy UI mode with optimized images and ES5 JavaScript

## How It Works

### User Experience

**Initial Setup (One-time, 10 minutes)**:

1. Deploy Docker container on home server/Raspberry Pi
2. Open web browser to admin interface
3. Upload family photos, organize into preset collections
4. Configure calendar URL (iCloud/Google Calendar ICS feed)
5. Set weather location
6. Point iPad browser to app URL
7. Enable guided access/kiosk mode on iPad

**Daily Use (Zero Intervention)**:

- Photos rotate automatically every 45 seconds (configurable)
- Calendar alarms pop up 15 minutes before family events
- Weather updates every 15 minutes
- Runs continuously without crashes or prompts

### Technical Flow

```
User uploads photos → FastAPI backend
    ↓
Photos optimized for iPad 2 (resize, JPEG conversion)
    ↓
Stored in preset folders on disk
    ↓
Slideshow endpoint randomly selects image
    ↓
Legacy UI displays optimized image
    ↓
Calendar service fetches ICS feeds every 10 minutes
    ↓
icalevents library parses events and recurrence
    ↓
Alarms displayed via HTMX polling
```

## User Experience Goals

### Primary User: Non-Technical Family Member

- "I want family photos displayed on the kitchen iPad"
- "I need reminders for kids' activities and appointments"
- "I want to see today's weather at a glance"
- "I don't want to fiddle with settings or troubleshoot"

### Secondary User: Technical Setup Person

- "I need simple Docker deployment"
- "Admin interface should be self-explanatory"
- "No debugging or log diving should be required"
- "Updates should be automated via Docker image pulls"

### Experience Principles

1. **Invisible Technology**: Once configured, should "just work" indefinitely
2. **Graceful Degradation**: Calendar sync failures don't break slideshow
3. **Instant Feedback**: Image uploads show preview immediately
4. **No Surprises**: Clear error messages when something goes wrong
5. **Respect Privacy**: All data stays on local network, no cloud dependencies

## Key Interactions

### Admin Interface (HTMX-driven)

- **Gallery Management**: Upload/delete photos, create preset collections
- **Calendar Sources**: Add/remove ICS feed URLs, test sync
- **Settings**: Configure active preset, slideshow duration, weather location
- **Debug Panel** (dev mode): View cached events, sync status, test alarms

### Slideshow View (Auto-refreshing)

- **Photo Display**: Full-screen image with smooth fade transitions
- **Alarm Pop-ups**: Non-intrusive overlay with event details and dismiss button
- **Weather Widget**: Corner display (temperature, conditions icon)
- **Clock/Date**: Always visible in local timezone

## Success Stories

### Target Scenarios

1. **Kitchen Display**: iPad mounted on wall, shows family photos between meal prep, pops up reminders for soccer practice
2. **Office Desk**: Shows personal photos during work, displays calendar for upcoming meetings
3. **Nursing Home**: Elderly parent's room displays rotating family photos, shows appointment reminders
4. **Teacher Classroom**: Displays class photos, shows bell schedule and recess reminders

## Related Documents

- [projectbrief.md](projectbrief.md) — Core requirements and constraints
- [systemPatterns.md](systemPatterns.md) — Technical patterns and architecture
- [CONTRIBUTING.md](../CONTRIBUTING.md) — How to contribute improvements
