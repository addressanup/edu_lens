/**
 * ChildSelector Component
 * Multi-child selector dropdown for switching between children's profiles
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  FlatList,
  Dimensions,
} from 'react-native';
import { ChildProfile } from '../../types';

interface ChildSelectorProps {
  children: ChildProfile[];
  selectedChild: ChildProfile | null;
  onSelectChild: (child: ChildProfile) => void;
  style?: any;
}

export const ChildSelector: React.FC<ChildSelectorProps> = ({
  children,
  selectedChild,
  onSelectChild,
  style,
}) => {
  const [modalVisible, setModalVisible] = useState(false);

  const handleSelectChild = (child: ChildProfile) => {
    onSelectChild(child);
    setModalVisible(false);
  };

  if (children.length === 0) {
    return null;
  }

  if (children.length === 1) {
    return (
      <View style={[styles.singleChildContainer, style]}>
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>
            {children[0].name.charAt(0).toUpperCase()}
          </Text>
        </View>
        <View style={styles.childInfo}>
          <Text style={styles.childName}>{children[0].name}</Text>
          <Text style={styles.childGrade}>Grade {children[0].grade}</Text>
        </View>
      </View>
    );
  }

  return (
    <>
      <TouchableOpacity
        style={[styles.selector, style]}
        onPress={() => setModalVisible(true)}
        activeOpacity={0.7}
      >
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>
            {selectedChild?.name.charAt(0).toUpperCase() || '?'}
          </Text>
        </View>
        <View style={styles.childInfo}>
          <Text style={styles.childName}>
            {selectedChild?.name || 'Select Child'}
          </Text>
          <Text style={styles.childGrade}>
            {selectedChild ? `Grade ${selectedChild.grade}` : 'Tap to select'}
          </Text>
        </View>
        <Text style={styles.chevron}>▼</Text>
      </TouchableOpacity>

      <Modal
        visible={modalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setModalVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setModalVisible(false)}
        >
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Child</Text>
              <TouchableOpacity
                onPress={() => setModalVisible(false)}
                style={styles.closeButton}
              >
                <Text style={styles.closeText}>✕</Text>
              </TouchableOpacity>
            </View>
            <FlatList
              data={children}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.childOption,
                    item.id === selectedChild?.id && styles.selectedOption,
                  ]}
                  onPress={() => handleSelectChild(item)}
                  activeOpacity={0.7}
                >
                  <View style={styles.avatarCircle}>
                    <Text style={styles.avatarText}>
                      {item.name.charAt(0).toUpperCase()}
                    </Text>
                  </View>
                  <View style={styles.childInfo}>
                    <Text style={styles.optionName}>{item.name}</Text>
                    <Text style={styles.optionGrade}>Grade {item.grade}</Text>
                  </View>
                  {item.id === selectedChild?.id && (
                    <Text style={styles.checkmark}>✓</Text>
                  )}
                </TouchableOpacity>
              )}
            />
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
};

const styles = StyleSheet.create({
  singleChildContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  selector: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  avatarCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#4A90A4',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  avatarText: {
    fontSize: 20,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  childInfo: {
    flex: 1,
  },
  childName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
  },
  childGrade: {
    fontSize: 13,
    color: '#666666',
    marginTop: 2,
  },
  chevron: {
    fontSize: 12,
    color: '#999999',
    marginLeft: 8,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    width: Dimensions.get('window').width - 64,
    maxHeight: 400,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#EEEEEE',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
  },
  closeButton: {
    padding: 4,
  },
  closeText: {
    fontSize: 20,
    color: '#999999',
  },
  childOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F5',
  },
  selectedOption: {
    backgroundColor: '#E8F4F8',
  },
  optionName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333333',
  },
  optionGrade: {
    fontSize: 13,
    color: '#666666',
    marginTop: 2,
  },
  checkmark: {
    fontSize: 18,
    color: '#4A90A4',
    fontWeight: '600',
  },
});
