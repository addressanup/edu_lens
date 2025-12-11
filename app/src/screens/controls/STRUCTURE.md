# Parental Controls - File Structure

## Directory Tree

```
/app/src/
├── screens/
│   └── controls/
│       ├── UsageLimitsScreen.tsx           (Time controls & scheduling)
│       ├── ContentFiltersScreen.tsx        (Content & subject filtering)
│       ├── NotificationsScreen.tsx         (Notification preferences)
│       ├── SafetySettingsScreen.tsx        (Safety & privacy controls)
│       ├── index.ts                        (Barrel export)
│       ├── README.md                       (Comprehensive documentation)
│       └── STRUCTURE.md                    (This file)
│
└── components/
    └── controls/
        ├── TimeSlider.tsx                  (Time limit slider component)
        ├── SchedulePicker.tsx              (Weekly schedule picker)
        ├── SubjectToggle.tsx               (Subject enable/disable toggle)
        ├── SafetyToggle.tsx                (Safety setting toggle)
        └── index.ts                        (Barrel export)
```

## File Sizes

| File | Lines | Purpose |
|------|-------|---------|
| UsageLimitsScreen.tsx | 446 | Time limits and usage schedules |
| ContentFiltersScreen.tsx | 594 | Content filtering and subjects |
| NotificationsScreen.tsx | 436 | Notification management |
| SafetySettingsScreen.tsx | 631 | Safety and privacy settings |
| TimeSlider.tsx | 100 | Reusable time slider |
| SchedulePicker.tsx | 311 | Weekly schedule picker |
| SubjectToggle.tsx | 133 | Subject toggle control |
| SafetyToggle.tsx | 189 | Safety toggle with levels |

**Total Lines**: ~2,840 lines of production code

## Quick Import Reference

### Screens
```typescript
import {
  UsageLimitsScreen,
  ContentFiltersScreen,
  NotificationsScreen,
  SafetySettingsScreen,
} from '@/screens/controls';
```

### Components
```typescript
import {
  TimeSlider,
  SchedulePicker,
  SubjectToggle,
  SafetyToggle,
} from '@/components/controls';
```

### Types
```typescript
import type {
  TimeSlot,
  WeeklySchedule,
  Subject,
  SafetySetting,
  SafetyLevel,
} from '@/components/controls';
```

## Feature Matrix

| Screen | Components Used | Store Integration | Key Features |
|--------|----------------|-------------------|--------------|
| UsageLimitsScreen | TimeSlider, SchedulePicker | useChild | Daily limits, breaks, schedules |
| ContentFiltersScreen | SubjectToggle | useChild | 8 subjects, difficulty, filters |
| NotificationsScreen | Custom toggles | useAuthStore | Multi-channel, quiet hours |
| SafetySettingsScreen | SafetyToggle | N/A | Privacy, security, emergency |

## Navigation Routes

```typescript
// Suggested route configuration
const routes = {
  UsageLimits: 'controls/usage-limits',
  ContentFilters: 'controls/content-filters',
  Notifications: 'controls/notifications',
  SafetySettings: 'controls/safety-settings',
};
```

## State Management

### UsageLimitsScreen
- Local state for limit values
- Syncs to `ChildPreferences`
- Updates via `useChild.updatePreferences()`

### ContentFiltersScreen
- Local state for subject toggles
- Syncs to `ChildPreferences.subjects[]`
- Updates difficulty level

### NotificationsScreen
- Local state for notification toggles
- Syncs to `UserPreferences`
- Updates via auth store

### SafetySettingsScreen
- Local state for all settings
- Emergency contact management
- PIN modal state

## Common Patterns

### Toggle Pattern
```typescript
const handleToggle = (key: string, value: boolean) => {
  setSettings(prev => ({ ...prev, [key]: value }));
  setHasChanges(true);
};
```

### Save Pattern
```typescript
const handleSave = async () => {
  const success = await updatePreferences(childId, preferences);
  if (success) {
    Alert.alert('Success', 'Settings updated');
    setHasChanges(false);
  }
};
```

### Empty State Pattern
```typescript
if (!activeChild) {
  return (
    <View style={styles.emptyState}>
      <Text>No child selected</Text>
    </View>
  );
}
```

## Styling Conventions

### Color Palette
- Primary: #4A90A4
- Secondary: #E8F4F8
- Background: #F8FAFB
- Danger: #FF5252
- Warning: #FFA726

### Common Styles
- Card margin: 16px bottom
- Section padding: 20px
- Border radius: 12px
- Toggle size: 51x31px

## Dependencies

### External
- @react-native-community/slider
- @react-navigation/native
- react-native

### Internal
- hooks/useChild
- hooks/useAuth
- store/slices/*
- components/common/*
- types/index

## Testing Strategy

### Unit Tests
- Component rendering
- Toggle state changes
- Time formatting
- Schedule manipulation

### Integration Tests
- Store updates
- Navigation flows
- Form validation
- API calls

### E2E Tests
- Complete setting flows
- Multi-screen workflows
- Data persistence
- Error handling

---

**Last Updated**: 2025-12-10
**Version**: 1.0.0
