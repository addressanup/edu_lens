/**
 * Common Input Component for EduLens App
 */

import React, { useState } from 'react';
import {
  View,
  TextInput,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInputProps,
  ViewStyle,
} from 'react-native';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  containerStyle?: ViewStyle;
  isPassword?: boolean;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  containerStyle,
  isPassword = false,
  ...textInputProps
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const inputContainerStyles = [
    styles.inputContainer,
    isFocused && styles.inputFocused,
    error && styles.inputError,
  ];

  return (
    <View style={[styles.container, containerStyle]}>
      {label && <Text style={styles.label}>{label}</Text>}

      <View style={inputContainerStyles}>
        {leftIcon && <View style={styles.iconContainer}>{leftIcon}</View>}

        <TextInput
          style={styles.input}
          placeholderTextColor="#999999"
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          secureTextEntry={isPassword && !showPassword}
          {...textInputProps}
        />

        {isPassword && (
          <TouchableOpacity
            style={styles.iconContainer}
            onPress={() => setShowPassword(!showPassword)}
          >
            <Text style={styles.showHideText}>
              {showPassword ? 'Hide' : 'Show'}
            </Text>
          </TouchableOpacity>
        )}

        {rightIcon && !isPassword && (
          <View style={styles.iconContainer}>{rightIcon}</View>
        )}
      </View>

      {error && <Text style={styles.errorText}>{error}</Text>}
      {hint && !error && <Text style={styles.hintText}>{hint}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    borderWidth: 2,
    borderColor: 'transparent',
    paddingHorizontal: 16,
  },
  inputFocused: {
    borderColor: '#4A90A4',
    backgroundColor: '#FFFFFF',
  },
  inputError: {
    borderColor: '#E74C3C',
  },
  input: {
    flex: 1,
    paddingVertical: 14,
    fontSize: 16,
    color: '#333333',
  },
  iconContainer: {
    marginRight: 8,
  },
  showHideText: {
    color: '#4A90A4',
    fontSize: 14,
    fontWeight: '500',
  },
  errorText: {
    color: '#E74C3C',
    fontSize: 12,
    marginTop: 4,
  },
  hintText: {
    color: '#666666',
    fontSize: 12,
    marginTop: 4,
  },
});
