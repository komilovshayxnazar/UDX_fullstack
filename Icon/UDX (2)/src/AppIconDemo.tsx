import { TranslationProvider } from './context/TranslationContext';
import { AppIconScreen } from './components/AppIconScreen';

// This is a standalone demo file to showcase the UDX application icon
// You can access this by temporarily changing the export in App.tsx

export default function AppIconDemo() {
  return (
    <TranslationProvider>
      <AppIconScreen />
    </TranslationProvider>
  );
}
