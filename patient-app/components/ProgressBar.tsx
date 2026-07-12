import { StyleSheet, Text, View } from 'react-native'

interface Props {
  current: number
  total: number
}

export function ProgressBar({ current, total }: Props) {
  const pct = total > 0 ? (current / total) * 100 : 0
  return (
    <View style={s.container}>
      <View style={s.track}>
        <View style={[s.fill, { width: `${pct}%` }]} />
      </View>
      <Text style={s.label}>{current} / {total}</Text>
    </View>
  )
}

const s = StyleSheet.create({
  container: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 8 },
  track: { height: 4, backgroundColor: '#e5e7eb', borderRadius: 2, overflow: 'hidden' },
  fill: { height: '100%', backgroundColor: '#2563eb', borderRadius: 2 },
  label: { fontSize: 12, color: '#6b7280', marginTop: 6, textAlign: 'right' },
})
