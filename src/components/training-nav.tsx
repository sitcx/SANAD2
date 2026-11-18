import { Link, useLocation } from '@tanstack/react-router';
import { Target, Video } from 'lucide-react';

export function TrainingNav() {
  const { pathname } = useLocation();
  return <nav className="training-nav" aria-label="التدريب والمقابلة"><Link to="/coach" data-active={pathname === '/coach'}><Target />التدريب</Link><Link to="/interview" data-active={pathname === '/interview'}><Video />المقابلة المباشرة</Link></nav>;
}