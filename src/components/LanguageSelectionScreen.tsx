import { useState } from 'react';
import { ArrowLeft, Check, Sparkles } from 'lucide-react';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { languages, type Language } from '../data/mockData';
import { useTranslation } from '../context/TranslationContext';

interface LanguageSelectionScreenProps {
  onBack: () => void;
  currentLanguage?: string;
  onLanguageSelect?: (languageCode: string) => void;
}

export function LanguageSelectionScreen({ 
  onBack, 
  currentLanguage = 'en',
  onLanguageSelect 
}: LanguageSelectionScreenProps) {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState(currentLanguage);

  // List of manually translated languages
  const manuallyTranslatedLanguages = ['en', 'ru', 'tr', 'zh', 'es', 'ar', 'fr', 'de', 'pt', 'hi', 'uz', 'kk', 'ky', 'tg', 'fa'];

  const filteredLanguages = languages.filter(lang => 
    lang.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    lang.nativeName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleLanguageSelect = (languageCode: string) => {
    setSelectedLanguage(languageCode);
    onLanguageSelect?.(languageCode);
    // Auto-close after selection
    setTimeout(() => {
      onBack();
    }, 300);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background px-4 py-4 shadow-sm">
        <div className="mb-4 flex items-center gap-3">
          <button onClick={onBack} className="rounded-full p-2 hover:bg-accent">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="flex-1">
            <h2>{t('language.title')}</h2>
            <div className="flex items-center gap-1 mt-1">
              <Sparkles className="h-3 w-3 text-[#af47ff]" />
              <span className="text-xs text-muted-foreground">200+ languages supported with auto-translation</span>
            </div>
          </div>
        </div>

        {/* Search */}
        <Input
          placeholder={t('common.search')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full"
        />
      </div>

      {/* Language List */}
      <div className="px-4 py-4">
        <Card className="overflow-hidden">
          {filteredLanguages.map((language, index) => {
            const isManuallyTranslated = manuallyTranslatedLanguages.includes(language.code);
            
            return (
              <div key={language.code}>
                {index > 0 && <div className="border-t" />}
                <button
                  onClick={() => handleLanguageSelect(language.code)}
                  className="flex w-full items-center gap-4 p-4 text-left hover:bg-background"
                >
                  <span className="text-3xl">{language.flag}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span>{language.name}</span>
                      {!isManuallyTranslated && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 text-xs">
                          <Sparkles className="h-2.5 w-2.5" />
                          Auto
                        </span>
                      )}
                    </div>
                    <div className="text-muted-foreground">{language.nativeName}</div>
                  </div>
                  {selectedLanguage === language.code && (
                    <Check className="h-5 w-5 text-[#af47ff]" />
                  )}
                </button>
              </div>
            );
          })}
        </Card>

        {filteredLanguages.length === 0 && (
          <div className="py-12 text-center text-muted-foreground">
            No languages found
          </div>
        )}
      </div>
    </div>
  );
}