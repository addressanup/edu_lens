/**
 * ProgressChart Component
 * Visualizes learning progress over time using react-native-chart-kit
 */

import React from 'react';
import { View, StyleSheet, Dimensions, Text } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { DataPoint } from '../../types';

interface ProgressChartProps {
  data: DataPoint[];
  title: string;
  color?: string;
  style?: any;
  height?: number;
}

export const ProgressChart: React.FC<ProgressChartProps> = ({
  data,
  title,
  color = '#4A90A4',
  style,
  height = 200,
}) => {
  if (!data || data.length === 0) {
    return (
      <View style={[styles.container, style]}>
        <Text style={styles.title}>{title}</Text>
        <View style={[styles.emptyState, { height }]}>
          <Text style={styles.emptyText}>No data available yet</Text>
        </View>
      </View>
    );
  }

  const labels = data.map((point) => {
    const date = new Date(point.date);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  });

  const values = data.map((point) => point.value);

  const chartData = {
    labels: labels.length > 7 ? labels.slice(-7) : labels,
    datasets: [
      {
        data: values.length > 7 ? values.slice(-7) : values,
        color: (opacity = 1) => color,
        strokeWidth: 2,
      },
    ],
  };

  const screenWidth = Dimensions.get('window').width - 64;

  return (
    <View style={[styles.container, style]}>
      <Text style={styles.title}>{title}</Text>
      <LineChart
        data={chartData}
        width={screenWidth}
        height={height}
        chartConfig={{
          backgroundColor: '#FFFFFF',
          backgroundGradientFrom: '#FFFFFF',
          backgroundGradientTo: '#FFFFFF',
          decimalPlaces: 0,
          color: (opacity = 1) => color,
          labelColor: (opacity = 1) => '#666666',
          style: {
            borderRadius: 16,
          },
          propsForDots: {
            r: '4',
            strokeWidth: '2',
            stroke: color,
          },
          propsForBackgroundLines: {
            strokeDasharray: '',
            stroke: '#EEEEEE',
            strokeWidth: 1,
          },
        }}
        bezier
        style={styles.chart}
        withInnerLines={true}
        withOuterLines={false}
        withVerticalLabels={true}
        withHorizontalLabels={true}
        withDots={true}
        withShadow={false}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 12,
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  emptyState: {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F9F9F9',
    borderRadius: 12,
  },
  emptyText: {
    fontSize: 14,
    color: '#999999',
  },
});
