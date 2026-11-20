import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';

export function RunsAreaChart({ runs }: { runs: any[] }) {
  // Process runs into last 7 days
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const today = new Date();
  const last7Days = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() - (6 - i));
    return { name: days[d.getDay()], dateStr: d.toDateString(), runs: 0 };
  });

  runs.forEach(run => {
    const runDate = new Date(run.created_at).toDateString();
    const dayMatch = last7Days.find(d => d.dateStr === runDate);
    if (dayMatch) dayMatch.runs += 1;
  });

  return (
    <div className="h-72 w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={last7Days} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorRuns" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
          <XAxis dataKey="name" stroke="#6B7280" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#6B7280" fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
          <RechartsTooltip 
            contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', borderRadius: '8px' }}
            itemStyle={{ color: '#fff' }}
          />
          <Area type="monotone" dataKey="runs" stroke="#8B5CF6" strokeWidth={2} fillOpacity={1} fill="url(#colorRuns)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StatusDonutChart({ runs }: { runs: any[] }) {
  const completed = runs.filter(r => r.status === 'completed').length;
  const pending = runs.filter(r => r.status === 'pending_approval').length;
  const failed = runs.filter(r => r.status === 'failed').length;

  const pieData = [
    { name: 'Completed', value: completed, color: '#10B981' },
    { name: 'Pending', value: pending, color: '#F59E0B' },
    { name: 'Failed', value: failed, color: '#EF4444' },
  ].filter(d => d.value > 0);

  // If no data, show a gray empty state ring
  const displayData = pieData.length ? pieData : [{ name: 'No Data', value: 1, color: '#374151' }];

  return (
    <div className="h-72 w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={displayData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={5}
            dataKey="value"
            stroke="none"
          >
            {displayData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          {pieData.length > 0 && (
            <RechartsTooltip 
              contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', borderRadius: '8px' }}
            />
          )}
          <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px', color: '#9CA3AF' }}/>
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}