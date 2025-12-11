/**
 * SchedulePicker Component
 * Weekly schedule picker for allowed hours
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ScrollView,
  ViewStyle,
} from 'react-native';

export interface TimeSlot {
  startHour: number;
  startMinute: number;
  endHour: number;
  endMinute: number;
}

export interface WeeklySchedule {
  monday: TimeSlot[];
  tuesday: TimeSlot[];
  wednesday: TimeSlot[];
  thursday: TimeSlot[];
  friday: TimeSlot[];
  saturday: TimeSlot[];
  sunday: TimeSlot[];
}

interface SchedulePickerProps {
  schedule: WeeklySchedule;
  onChange: (schedule: WeeklySchedule) => void;
  style?: ViewStyle;
}

type DayOfWeek = keyof WeeklySchedule;

const DAYS: { key: DayOfWeek; label: string }[] = [
  { key: 'monday', label: 'Monday' },
  { key: 'tuesday', label: 'Tuesday' },
  { key: 'wednesday', label: 'Wednesday' },
  { key: 'thursday', label: 'Thursday' },
  { key: 'friday', label: 'Friday' },
  { key: 'saturday', label: 'Saturday' },
  { key: 'sunday', label: 'Sunday' },
];

export const SchedulePicker: React.FC<SchedulePickerProps> = ({
  schedule,
  onChange,
  style,
}) => {
  const [selectedDay, setSelectedDay] = useState<DayOfWeek | null>(null);
  const [showModal, setShowModal] = useState(false);

  const formatTimeSlot = (slot: TimeSlot): string => {
    const formatTime = (hour: number, minute: number): string => {
      const period = hour >= 12 ? 'PM' : 'AM';
      const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
      const displayMinute = minute.toString().padStart(2, '0');
      return `${displayHour}:${displayMinute} ${period}`;
    };

    return `${formatTime(slot.startHour, slot.startMinute)} - ${formatTime(slot.endHour, slot.endMinute)}`;
  };

  const getDayStatus = (day: DayOfWeek): string => {
    const slots = schedule[day];
    if (slots.length === 0) return 'Not allowed';
    if (slots.length === 1 && slots[0].startHour === 0 && slots[0].endHour === 23) {
      return 'All day';
    }
    return `${slots.length} slot${slots.length > 1 ? 's' : ''}`;
  };

  const addTimeSlot = (day: DayOfWeek) => {
    const newSlot: TimeSlot = {
      startHour: 9,
      startMinute: 0,
      endHour: 17,
      endMinute: 0,
    };

    onChange({
      ...schedule,
      [day]: [...schedule[day], newSlot],
    });
  };

  const removeTimeSlot = (day: DayOfWeek, index: number) => {
    const updatedSlots = schedule[day].filter((_, i) => i !== index);
    onChange({
      ...schedule,
      [day]: updatedSlots,
    });
  };

  const setAllDay = (day: DayOfWeek) => {
    onChange({
      ...schedule,
      [day]: [
        {
          startHour: 0,
          startMinute: 0,
          endHour: 23,
          endMinute: 59,
        },
      ],
    });
  };

  const clearDay = (day: DayOfWeek) => {
    onChange({
      ...schedule,
      [day]: [],
    });
  };

  const openDayEditor = (day: DayOfWeek) => {
    setSelectedDay(day);
    setShowModal(true);
  };

  const closeDayEditor = () => {
    setSelectedDay(null);
    setShowModal(false);
  };

  return (
    <View style={[styles.container, style]}>
      {DAYS.map((day) => (
        <TouchableOpacity
          key={day.key}
          style={styles.dayRow}
          onPress={() => openDayEditor(day.key)}
        >
          <View style={styles.dayInfo}>
            <Text style={styles.dayLabel}>{day.label}</Text>
            <Text style={styles.dayStatus}>{getDayStatus(day.key)}</Text>
          </View>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
      ))}

      <Modal
        visible={showModal}
        animationType="slide"
        transparent={true}
        onRequestClose={closeDayEditor}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {selectedDay && DAYS.find((d) => d.key === selectedDay)?.label}
              </Text>
              <TouchableOpacity onPress={closeDayEditor}>
                <Text style={styles.closeButton}>Done</Text>
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              {selectedDay && schedule[selectedDay].length > 0 && (
                <View style={styles.slotsContainer}>
                  {schedule[selectedDay].map((slot, index) => (
                    <View key={index} style={styles.slotCard}>
                      <Text style={styles.slotTime}>{formatTimeSlot(slot)}</Text>
                      <TouchableOpacity
                        onPress={() => removeTimeSlot(selectedDay, index)}
                        style={styles.removeButton}
                      >
                        <Text style={styles.removeButtonText}>Remove</Text>
                      </TouchableOpacity>
                    </View>
                  ))}
                </View>
              )}

              {selectedDay && schedule[selectedDay].length === 0 && (
                <View style={styles.emptyState}>
                  <Text style={styles.emptyText}>No time slots set</Text>
                  <Text style={styles.emptySubtext}>
                    Add time slots to allow usage on this day
                  </Text>
                </View>
              )}

              <View style={styles.actions}>
                {selectedDay && (
                  <>
                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => addTimeSlot(selectedDay)}
                    >
                      <Text style={styles.actionButtonText}>Add Time Slot</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => setAllDay(selectedDay)}
                    >
                      <Text style={styles.actionButtonText}>Set All Day</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={[styles.actionButton, styles.clearButton]}
                      onPress={() => clearDay(selectedDay)}
                    >
                      <Text style={[styles.actionButtonText, styles.clearButtonText]}>
                        Clear All
                      </Text>
                    </TouchableOpacity>
                  </>
                )}
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
  },
  dayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  dayInfo: {
    flex: 1,
  },
  dayLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 4,
  },
  dayStatus: {
    fontSize: 14,
    color: '#999999',
  },
  chevron: {
    fontSize: 24,
    color: '#CCCCCC',
    fontWeight: '300',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#333333',
  },
  closeButton: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4A90A4',
  },
  modalBody: {
    padding: 20,
  },
  slotsContainer: {
    marginBottom: 20,
  },
  slotCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#F8FAFB',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  slotTime: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
  },
  removeButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  removeButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF5252',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999999',
    textAlign: 'center',
  },
  actions: {
    gap: 12,
  },
  actionButton: {
    backgroundColor: '#E8F4F8',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4A90A4',
  },
  clearButton: {
    backgroundColor: '#FFE8E8',
  },
  clearButtonText: {
    color: '#FF5252',
  },
});
