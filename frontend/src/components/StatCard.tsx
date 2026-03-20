import type { ReactNode } from "react";
import { Card, Skeleton, Statistic } from "antd";

interface StatCardProps {
  title: string;
  value: number | string;
  icon: ReactNode;
  prefix?: string;
  suffix?: string;
  loading?: boolean;
}

export default function StatCard({
  title,
  value,
  icon,
  prefix,
  suffix,
  loading,
}: StatCardProps) {
  if (loading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 1 }} />
      </Card>
    );
  }

  return (
    <Card>
      <Statistic
        title={title}
        value={value}
        prefix={
          <>
            {icon}
            {prefix ? <span style={{ marginLeft: 4 }}>{prefix}</span> : null}
          </>
        }
        suffix={suffix}
      />
    </Card>
  );
}
