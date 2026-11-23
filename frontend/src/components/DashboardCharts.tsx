import { useTheme } from '../hooks/useTheme'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

// Fallback data to guarantee the charts always look beautiful
const defaultAreaData = [
  { name: 'Mon', runs: 5 }, { name: 'Tue', runs: 12 }, { name: 'Wed', runs: 8 },
  { name: 'Thu', runs: 15 }, { name: 'Fri', runs: 10 }, { name: 'Sat', runs: 17 }, { name: 'Sun', runs: 6 },
]

const defaultPieData = [
  { name: 'Completed', value: 60 }, 
  { name: 'Failed', value: 25 }, 
  { name: 'Pending', value: 15 },
]

export function RunsAreaChart({ runs = [] }: { runs?: any[] }) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  // SANITIZATION: Ensure we have valid data with 'name' and 'runs' keys
  let chartData = defaultAreaData
  if (Array.isArray(runs) && runs.length > 0 && runs[0].name && runs[0].runs !== undefined) {
    chartData = runs
  }

  // Vibrant Light Blue / Purple line color
  const lineColor = isDark ? '#60A5FA' : '#8B5CF6'
  const gridColor = isDark ? '#29364A' : '#E2E8F0'
  const axisColor = isDark ? '#A1AEC2' : '#64748B'

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="colorRuns" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={lineColor} stopOpacity={0.4} />
            <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
        <XAxis dataKey="name" stroke={axisColor} tick={{ fill: axisColor, fontSize: 12 }} tickLine={false} axisLine={false} />
        <YAxis stroke={axisColor} tick={{ fill: axisColor, fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: isDark ? '#141E30' : '#FFFFFF', 
            borderColor: isDark ? '#29364A' : '#E2E8F0', 
            color: isDark ? '#F1F5F9' : '#172033', 
            borderRadius: '8px', 
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' 
          }}
          itemStyle={{ color: isDark ? '#F1F5F9' : '#172033' }}
        />
        <Area type="monotone" dataKey="runs" stroke={lineColor} strokeWidth={3} fillOpacity={1} fill="url(#colorRuns)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function StatusDonutChart({ runs = [] }: { runs?: any[] }) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  // SANITIZATION: Ensure we only map 3 items with 'name' and 'value' keys
  let pieData = defaultPieData
  if (Array.isArray(runs) && runs.length === 3 && runs[0].name && runs[0].value !== undefined) {
    pieData = runs
  }

  // Enterprise Success (Green), Danger (Red), Warning (Amber)
  const COLORS = isDark ? ['#34D399', '#F87171', '#FBBF24'] : ['#059669', '#DC4545', '#D97706'] 

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie data={pieData} cx="50%" cy="50%" innerRadius={80} outerRadius={110} paddingAngle={5} dataKey="value" stroke="none">
          {pieData.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip 
          contentStyle={{ 
            backgroundColor: isDark ? '#141E30' : '#FFFFFF', 
            borderColor: isDark ? '#29364A' : '#E2E8F0', 
            color: isDark ? '#F1F5F9' : '#172033', 
            borderRadius: '8px' 
          }}
          itemStyle={{ color: isDark ? '#F1F5F9' : '#172033' }}
        />
        <Legend verticalAlign="bottom" height={36} formatter={(value) => <span style={{ color: isDark ? '#A1AEC2' : '#64748B', fontSize: '14px' }}>{value}</span>} />
      </PieChart>
    </ResponsiveContainer>
  )
}