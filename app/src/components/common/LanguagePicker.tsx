/**
 * LanguagePicker Component
 *
 * Dropdown selector for choosing child's preferred language.
 * Supports 7 languages for EduLens multi-language tutoring.
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

export interface LanguageOption {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
}

// Supported languages for EduLens
export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇲🇽' },
  { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
  { code: 'zh', name: 'Chinese', nativeName: '中文', flag: '🇨🇳' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', flag: '🇮🇳' },
  { code: 'ne', name: 'Nepali', nativeName: 'नेपाली', flag: '🇳🇵' },
];

interface LanguagePickerProps {
  selectedLanguage: string;
  onSelectLanguage: (language: string) => void;
  label?: string;
  error?: string;
  disabled?: boolean;
}

export const LanguagePicker: React.FC<LanguagePickerProps> = ({
  selectedLanguage,
  onSelectLanguage,
  label = 'Preferred Language',
  error,
  disabled = false,
}) => {
  const [modalVisible, setModalVisible] = useState(false);

  const selectedLang = SUPPORTED_LANGUAGES.find(l => l.code === selectedLanguage)
    || SUPPORTED_LANGUAGES[0];

  const handleSelectLanguage = (lang: LanguageOption) => {
    onSelectLanguage(lang.code);
    setModalVisible(false);
  };

  return (
    <View style={styles.container}>
      {label && <Text style={styles.label}>{label}</Text>}

      <TouchableOpacity
        style={[
          styles.selector,
          error && styles.selectorError,
          disabled && styles.selectorDisabled,
        ]}
        onPress={() => !disabled && setModalVisible(true)}
        activeOpacity={disabled ? 1 : 0.7}
      >
        <Text style={styles.flag}>{selectedLang.flag}</Text>
        <View style={styles.languageInfo}>
          <Text style={styles.languageName}>{selectedLang.name}</Text>
          <Text style={styles.nativeName}>{selectedLang.nativeName}</Text>
        </View>
        <Text style={styles.chevron}>▼</Text>
      </TouchableOpacity>

      {error && <Text style={styles.errorText}>{error}</Text>}

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
              <Text style={styles.modalTitle}>Select Language</Text>
              <TouchableOpacity
                onPress={() => setModalVisible(false)}
                style={styles.closeButton}
              >
                <Text style={styles.closeText}>✕</Text>
              </TouchableOpacity>
            </View>
            <FlatList
              data={SUPPORTED_LANGUAGES}
              keyExtractor={(item) => item.code}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.languageOption,
                    item.code === selectedLanguage && styles.selectedOption,
                  ]}
                  onPress={() => handleSelectLanguage(item)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.optionFlag}>{item.flag}</Text>
                  <View style={styles.optionInfo}>
                    <Text style={styles.optionName}>{item.name}</Text>
                    <Text style={styles.optionNative}>{item.nativeName}</Text>
                  </View>
                  {item.code === selectedLanguage && (
                    <Text style={styles.checkmark}>✓</Text>
                  )}
                </TouchableOpacity>
              )}
            />
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#334155',
    marginBottom: 8,
  },
  selector: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  selectorError: {
    borderColor: '#ef4444',
  },
  selectorDisabled: {
    backgroundColor: '#f1f5f9',
    opacity: 0.7,
  },
  flag: {
    fontSize: 24,
    marginRight: 12,
  },
  languageInfo: {
    flex: 1,
  },
  languageName: {
    fontSize: 16,
    color: '#1e293b',
    fontWeight: '500',
  },
  nativeName: {
    fontSize: 13,
    color: '#64748b',
    marginTop: 2,
  },
  chevron: {
    fontSize: 12,
    color: '#64748b',
  },
  errorText: {
    color: '#ef4444',
    fontSize: 12,
    marginTop: 4,
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
    maxHeight: 450,
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
  languageOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F5',
  },
  selectedOption: {
    backgroundColor: '#eff6ff',
  },
  optionFlag: {
    fontSize: 28,
    marginRight: 12,
  },
  optionInfo: {
    flex: 1,
  },
  optionName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333333',
  },
  optionNative: {
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

export default LanguagePicker;
