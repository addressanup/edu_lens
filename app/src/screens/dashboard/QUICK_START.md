# Dashboard Quick Start Guide

## Quick Import & Use

### Import Screens
```typescript
import {
  OverviewScreen,
  ProgressScreen,
  ActivityScreen,
  AchievementsScreen,
} from './screens/dashboard';
```

### Import Components
```typescript
import {
  ChildSelector,
  ProgressChart,
  SubjectCard,
  ActivityItem,
  AchievementBadge,
} from './components/dashboard';
```

---

## Usage Examples

### 1. OverviewScreen
```typescript
// In your navigator
<Stack.Screen
  name="Overview"
  component={OverviewScreen}
  options={{ title: 'Dashboard' }}
/>

// Standalone usage
<OverviewScreen />
```

**Features:**
- Auto-loads mock data on mount
- Pull-to-refresh support
- Multi-child selector
- Weekly progress chart
- Recent activities list

---

### 2. ProgressScreen
```typescript
// In your navigator
<Stack.Screen
  name="Progress"
  component={ProgressScreen}
  options={{ title: 'Learning Progress' }}
/>

// Standalone usage
<ProgressScreen />
```

**Features:**
- Time period selector (week/month/year/all)
- Subject breakdown cards
- Trend charts
- Strengths and improvements

---

### 3. ActivityScreen
```typescript
// In your navigator
<Stack.Screen
  name="Activity"
  component={ActivityScreen}
  options={{ title: 'Activity Log' }}
/>

// Standalone usage
<ActivityScreen />
```

**Features:**
- Date and type filtering
- Activity summary stats
- Export functionality
- Empty states

---

### 4. AchievementsScreen
```typescript
// In your navigator
<Stack.Screen
  name="Achievements"
  component={AchievementsScreen}
  options={{ title: 'Achievements' }}
/>

// Standalone usage
<AchievementsScreen />
```

**Features:**
- Earned and locked achievements
- Streak tracking
- Category filtering
- Detail modals

---

## Component Usage

### ChildSelector
```typescript
import { ChildSelector } from './components/dashboard';

<ChildSelector
  children={childrenArray}
  selectedChild={currentChild}
  onSelectChild={(child) => setCurrentChild(child)}
  style={{ marginBottom: 16 }}
/>
```

**Props:**
- `children: ChildProfile[]` - Array of child profiles
- `selectedChild: ChildProfile | null` - Currently selected child
- `onSelectChild: (child: ChildProfile) => void` - Selection callback
- `style?: any` - Optional custom styles

---

### ProgressChart
```typescript
import { ProgressChart } from './components/dashboard';

<ProgressChart
  data={dataPoints}
  title="Weekly Progress"
  color="#4A90A4"
  height={200}
/>
```

**Props:**
- `data: DataPoint[]` - Array of {date, value} objects
- `title: string` - Chart title
- `color?: string` - Line color (default: '#4A90A4')
- `height?: number` - Chart height (default: 200)
- `style?: any` - Optional custom styles

**DataPoint Format:**
```typescript
interface DataPoint {
  date: string; // ISO string
  value: number; // Numeric value
}
```

---

### SubjectCard
```typescript
import { SubjectCard } from './components/dashboard';

<SubjectCard
  subject={subjectData}
  onPress={() => console.log('Subject clicked')}
  style={{ marginBottom: 12 }}
/>
```

**Props:**
- `subject: SubjectProgress` - Subject progress data
- `onPress?: () => void` - Optional click handler
- `style?: any` - Optional custom styles

**SubjectProgress Format:**
```typescript
interface SubjectProgress {
  subject: string;           // e.g., "Math"
  duration: number;          // seconds
  questionsAsked: number;
  confidenceLevel: number;   // 0-100
  improvement: number;       // percentage change
}
```

---

### ActivityItem
```typescript
import { ActivityItem } from './components/dashboard';

<ActivityItem
  activity={activityData}
  onPress={() => console.log('Activity clicked')}
  style={{ marginBottom: 8 }}
/>
```

**Props:**
- `activity: LearningActivity` - Activity data
- `onPress?: () => void` - Optional click handler
- `style?: any` - Optional custom styles

---

### AchievementBadge
```typescript
import { AchievementBadge } from './components/dashboard';

// Earned achievement
<AchievementBadge
  achievement={achievementData}
  size="medium"
  onPress={() => showDetails(achievementData)}
/>

// Locked achievement with progress
<AchievementBadge
  achievement={achievementData}
  locked={true}
  progress={65}
  size="medium"
/>
```

**Props:**
- `achievement: Achievement` - Achievement data
- `locked?: boolean` - Is achievement locked? (default: false)
- `progress?: number` - Progress 0-100 (for locked achievements)
- `onPress?: () => void` - Optional click handler
- `size?: 'small' | 'medium' | 'large'` - Badge size (default: 'medium')
- `style?: any` - Optional custom styles

---

## Tab Navigation Setup

```typescript
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import {
  OverviewScreen,
  ProgressScreen,
  ActivityScreen,
  AchievementsScreen,
} from './screens/dashboard';

const Tab = createBottomTabNavigator();

function DashboardTabs() {
  return (
    <Tab.Navigator>
      <Tab.Screen
        name="Overview"
        component={OverviewScreen}
        options={{
          tabBarLabel: 'Home',
          tabBarIcon: ({ color, size }) => (
            <Icon name="home" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Progress"
        component={ProgressScreen}
        options={{
          tabBarLabel: 'Progress',
          tabBarIcon: ({ color, size }) => (
            <Icon name="chart-line" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Activity"
        component={ActivityScreen}
        options={{
          tabBarLabel: 'Activity',
          tabBarIcon: ({ color, size }) => (
            <Icon name="list" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Achievements"
        component={AchievementsScreen}
        options={{
          tabBarLabel: 'Awards',
          tabBarIcon: ({ color, size }) => (
            <Icon name="trophy" size={size} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}
```

---

## API Integration Template

Replace mock data with actual API calls:

```typescript
import { apiClient } from '../services/api';

// In your screen component
const loadData = async () => {
  try {
    // Fetch data from API
    const response = await apiClient.get('/children/{childId}/progress');

    // Update state with real data
    setProgressData(response.data);
  } catch (error) {
    console.error('Failed to load data:', error);
    // Handle error (show toast, etc.)
  }
};

useEffect(() => {
  loadData();
}, [childId]);
```

---

## State Management Integration

### Using Zustand

```typescript
import { create } from 'zustand';

interface DashboardStore {
  selectedChild: ChildProfile | null;
  progressData: LearningProgress | null;
  setSelectedChild: (child: ChildProfile) => void;
  loadProgress: (childId: string) => Promise<void>;
}

const useDashboardStore = create<DashboardStore>((set) => ({
  selectedChild: null,
  progressData: null,
  setSelectedChild: (child) => set({ selectedChild: child }),
  loadProgress: async (childId) => {
    const data = await fetchProgress(childId);
    set({ progressData: data });
  },
}));

// In your component
function OverviewScreen() {
  const { selectedChild, setSelectedChild } = useDashboardStore();
  // ... rest of component
}
```

---

## Styling Customization

### Override Default Colors

```typescript
import { OverviewScreen } from './screens/dashboard';

// Wrap with custom theme provider
<ThemeProvider theme={customTheme}>
  <OverviewScreen />
</ThemeProvider>

// Or use inline style overrides
<SubjectCard
  subject={subject}
  style={{
    backgroundColor: '#custom-color',
    borderRadius: 20,
  }}
/>
```

### Custom Subject Colors

```typescript
// In SubjectCard.tsx, modify SUBJECT_COLORS
const SUBJECT_COLORS: Record<string, string> = {
  Math: '#YOUR_COLOR',
  Reading: '#YOUR_COLOR',
  Science: '#YOUR_COLOR',
  // ...
};
```

---

## Common Patterns

### Loading States

```typescript
const [isLoading, setIsLoading] = useState(false);

const loadData = async () => {
  setIsLoading(true);
  try {
    const data = await fetchData();
    setData(data);
  } catch (error) {
    handleError(error);
  } finally {
    setIsLoading(false);
  }
};

// In render
{isLoading ? <LoadingSpinner /> : <DataView data={data} />}
```

### Error Handling

```typescript
const [error, setError] = useState<string | null>(null);

const loadData = async () => {
  try {
    const data = await fetchData();
    setData(data);
    setError(null);
  } catch (err) {
    setError(err.message);
    showToast('Failed to load data');
  }
};

// In render
{error && <ErrorBanner message={error} />}
```

### Pagination

```typescript
const [page, setPage] = useState(1);
const [hasMore, setHasMore] = useState(true);

const loadMore = async () => {
  if (!hasMore) return;

  const newData = await fetchPage(page + 1);
  setActivities([...activities, ...newData]);
  setPage(page + 1);
  setHasMore(newData.length > 0);
};

// In FlatList
<FlatList
  data={activities}
  onEndReached={loadMore}
  onEndReachedThreshold={0.5}
/>
```

---

## Troubleshooting

### Chart not displaying
```typescript
// Ensure data is in correct format
const data = [
  { date: '2024-12-01', value: 25 },
  { date: '2024-12-02', value: 30 },
];

// Check screen width
import { Dimensions } from 'react-native';
const screenWidth = Dimensions.get('window').width;
```

### Modal not closing
```typescript
// Ensure state is properly managed
const [visible, setVisible] = useState(false);

<Modal
  visible={visible}
  onRequestClose={() => setVisible(false)}
>
  <TouchableOpacity onPress={() => setVisible(false)}>
    <Text>Close</Text>
  </TouchableOpacity>
</Modal>
```

### Empty state showing incorrectly
```typescript
// Check data loading sequence
useEffect(() => {
  loadData(); // Ensure this runs
}, []);

// Check empty condition
{data.length === 0 ? <EmptyState /> : <DataList />}
```

---

## Performance Tips

1. **Use FlatList for long lists:**
```typescript
<FlatList
  data={activities}
  renderItem={({ item }) => <ActivityItem activity={item} />}
  keyExtractor={(item) => item.id}
  maxToRenderPerBatch={10}
  windowSize={5}
/>
```

2. **Memoize expensive calculations:**
```typescript
const totalHours = useMemo(() => {
  return activities.reduce((sum, a) => sum + a.duration, 0) / 3600;
}, [activities]);
```

3. **Optimize re-renders:**
```typescript
const MemoizedCard = React.memo(SubjectCard);
```

---

## Testing

### Component Test Example

```typescript
import { render, fireEvent } from '@testing-library/react-native';
import { OverviewScreen } from './OverviewScreen';

test('renders overview correctly', () => {
  const { getByText } = render(<OverviewScreen />);
  expect(getByText('Welcome back!')).toBeTruthy();
});

test('handles child selection', () => {
  const mockOnSelect = jest.fn();
  const { getByText } = render(
    <ChildSelector
      children={mockChildren}
      selectedChild={null}
      onSelectChild={mockOnSelect}
    />
  );

  fireEvent.press(getByText('Emma'));
  expect(mockOnSelect).toHaveBeenCalled();
});
```

---

## Support & Resources

- **Full Documentation:** `README.md`
- **Task Summary:** `/edu_lens/TASK_APP-001-T4_SUMMARY.md`
- **Type Definitions:** `/app/src/types/index.ts`
- **Common Components:** `/app/src/components/common/`

---

## Quick Reference

| Screen | Purpose | Key Feature |
|--------|---------|-------------|
| OverviewScreen | Main dashboard | Today's summary + charts |
| ProgressScreen | Detailed progress | Subject breakdown |
| ActivityScreen | Activity log | Filtering + export |
| AchievementsScreen | Achievements | Badges + streaks |

| Component | Purpose | Props |
|-----------|---------|-------|
| ChildSelector | Switch children | children, selectedChild, onSelectChild |
| ProgressChart | Visualize trends | data, title, color |
| SubjectCard | Show subject progress | subject, onPress |
| ActivityItem | Display activity | activity, onPress |
| AchievementBadge | Show achievement | achievement, locked, progress |

---

**Last Updated:** December 10, 2024
**Version:** 1.0.0
**Status:** Production Ready
