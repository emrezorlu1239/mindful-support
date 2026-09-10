import { Info } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export function LanguageNotice({ language }: { language: 'en' | 'tr' }) {
  return (
    <Alert className="language-caution" role="note">
      <Info aria-hidden="true" />
      <AlertTitle>
        {language === 'tr' ? 'Türkçe desteği sınırlıdır.' : 'Turkish support is limited.'}
      </AlertTitle>
      <AlertDescription>
        {language === 'tr'
          ? 'Türkçe yanıtlar anlam ve ifade hataları içerebilir, söylediklerini yanlış yorumlayabilir. Daha tutarlı yanıtlar için İngilizceyi tercih et. Yanıtları sağlık kararı vermek için kullanma; bu uygulama profesyonel desteğin yerini tutmaz.'
          : 'Turkish replies may contain wording and meaning errors or misinterpret what you say. Choose English for more consistent replies. Do not use replies to make health decisions; this app does not replace professional support.'}
      </AlertDescription>
    </Alert>
  );
}
