import React, { useState } from 'react';
import { AppIcon } from './AppIcon';
import { Download, Copy, Check, Palette } from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { useTranslation } from '../context/TranslationContext';

export function AppIconScreen() {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const [primaryColor, setPrimaryColor] = useState('#af47ff');

  const downloadSVG = () => {
    const svgString = `<svg width="512" height="512" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="256" cy="256" r="256" fill="${primaryColor}"/>
  <path d="M160 380 L160 200 M140 220 Q140 210, 150 210 Q160 210, 160 220 M140 240 Q140 230, 150 230 Q160 230, 160 240 M140 260 Q140 250, 150 250 Q160 250, 160 260 M140 280 Q140 270, 150 270 Q160 270, 160 280 M140 300 Q140 290, 150 290 Q160 290, 160 300" stroke="white" stroke-width="8" stroke-linecap="round" fill="none"/>
  <path d="M180 220 Q180 210, 170 210 Q160 210, 160 220 M180 240 Q180 230, 170 230 Q160 230, 160 240 M180 260 Q180 250, 170 250 Q160 250, 160 260 M180 280 Q180 270, 170 270 Q160 270, 160 280 M180 300 Q180 290, 170 290 Q160 290, 160 300" stroke="white" stroke-width="8" stroke-linecap="round" fill="none"/>
  <g transform="translate(240, 180)">
    <path d="M10 30 L30 30 L50 120 L120 120" stroke="white" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <path d="M50 120 L120 120 L110 180 L60 180 Z" fill="white" stroke="white" stroke-width="8" stroke-linejoin="round"/>
    <circle cx="70" cy="200" r="12" fill="white"/>
    <circle cx="110" cy="200" r="12" fill="white"/>
    <line x1="55" y1="120" x2="60" y2="160" stroke="${primaryColor}" stroke-width="8" stroke-linecap="round"/>
    <line x1="75" y1="120" x2="75" y2="165" stroke="${primaryColor}" stroke-width="8" stroke-linecap="round"/>
    <line x1="95" y1="120" x2="90" y2="165" stroke="${primaryColor}" stroke-width="8" stroke-linecap="round"/>
  </g>
  <path d="M140 140 L140 100 Q140 70, 170 70 Q200 70, 200 100 L200 140" stroke="white" stroke-width="16" stroke-linecap="round" fill="none" opacity="0.4"/>
  <path d="M210 260 L240 260 M220 250 L230 260 L220 270" stroke="rgba(255,255,255,0.6)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>`;
    
    const blob = new Blob([svgString], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'udx-icon.svg';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const downloadPNG = async (size: number) => {
    const svgString = `<svg width="${size}" height="${size}" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="256" cy="256" r="256" fill="${primaryColor}"/>
  <path d="M160 380 L160 200 M140 220 Q140 210, 150 210 Q160 210, 160 220 M140 240 Q140 230, 150 230 Q160 230, 160 240 M140 260 Q140 250, 150 250 Q160 250, 160 260 M140 280 Q140 270, 150 270 Q160 270, 160 280 M140 300 Q140 290, 150 290 Q160 290, 160 300" stroke="white" stroke-width="8" stroke-linecap="round" fill="none"/>
  <path d="M180 220 Q180 210, 170 210 Q160 210, 160 220 M180 240 Q180 230, 170 230 Q160 230, 160 240 M180 260 Q180 250, 170 250 Q160 250, 160 260 M180 280 Q180 270, 170 270 Q160 270, 160 280 M180 300 Q180 290, 170 290 Q160 290, 160 300" stroke="white" stroke-width="8" stroke-linecap="round" fill="none"/>
  <g transform="translate(240, 180)">
    <path d="M10 30 L30 30 L50 120 L120 120" stroke="white" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <path d="M50 120 L120 120 L110 180 L60 180 Z" fill="white" stroke="white" stroke-width="8" stroke-linejoin="round"/>
    <circle cx="70" cy="200" r="12" fill="white"/>
    <circle cx="110" cy="200" r="12" fill="white"/>
    <line x1="55" y1="120" x2="60" y2="160" stroke="${primaryColor}" stroke-width="8" stroke-linecap="round"/>
    <line x1="75" y1="120" x2="75" y2="165" stroke="${primaryColor}" stroke-width="8" stroke-linecap="round"/>
    <line x1="95" y1="120" x2="90" y2="165" stroke="${primaryColor}" stroke-width="8" stroke-linecap="round"/>
  </g>
  <path d="M140 140 L140 100 Q140 70, 170 70 Q200 70, 200 100 L200 140" stroke="white" stroke-width="16" stroke-linecap="round" fill="none" opacity="0.4"/>
  <path d="M210 260 L240 260 M220 250 L230 260 L220 270" stroke="rgba(255,255,255,0.6)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>`;

    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    const img = new Image();
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    
    img.onload = () => {
      ctx?.drawImage(img, 0, 0);
      canvas.toBlob((blob) => {
        if (blob) {
          const pngUrl = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = pngUrl;
          link.download = `udx-icon-${size}x${size}.png`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(pngUrl);
        }
      });
      URL.revokeObjectURL(url);
    };
    
    img.src = url;
  };

  const copyColorCode = () => {
    navigator.clipboard.writeText(primaryColor);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const presetColors = [
    { name: 'UDX Purple', color: '#af47ff' },
    { name: 'Deep Purple', color: '#8b2de6' },
    { name: 'Vibrant Purple', color: '#c566ff' },
    { name: 'Forest Green', color: '#2d7a2d' },
    { name: 'Emerald', color: '#10b981' },
    { name: 'Ocean Blue', color: '#0ea5e9' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-white p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            UDX Application Icon
          </h1>
          <p className="text-gray-600">
            Your agricultural marketplace brand identity
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Icon Preview */}
          <div>
            <Card className="p-8">
              <h2 className="text-xl font-semibold mb-6">Icon Preview</h2>
              
              {/* Large preview */}
              <div className="bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl p-12 mb-6 flex items-center justify-center">
                <div 
                  className="rounded-3xl shadow-2xl overflow-hidden"
                  style={{ 
                    width: '256px', 
                    height: '256px',
                    background: primaryColor 
                  }}
                >
                  <AppIcon size={256} />
                </div>
              </div>

              {/* Size previews */}
              <div className="flex items-center justify-center gap-6 mb-6">
                <div className="text-center">
                  <div 
                    className="rounded-xl shadow-lg overflow-hidden mx-auto mb-2"
                    style={{ 
                      width: '128px', 
                      height: '128px',
                      background: primaryColor 
                    }}
                  >
                    <AppIcon size={128} />
                  </div>
                  <span className="text-xs text-gray-500">128px</span>
                </div>
                <div className="text-center">
                  <div 
                    className="rounded-lg shadow-md overflow-hidden mx-auto mb-2"
                    style={{ 
                      width: '64px', 
                      height: '64px',
                      background: primaryColor 
                    }}
                  >
                    <AppIcon size={64} />
                  </div>
                  <span className="text-xs text-gray-500">64px</span>
                </div>
                <div className="text-center">
                  <div 
                    className="rounded-md shadow overflow-hidden mx-auto mb-2"
                    style={{ 
                      width: '32px', 
                      height: '32px',
                      background: primaryColor 
                    }}
                  >
                    <AppIcon size={32} />
                  </div>
                  <span className="text-xs text-gray-500">32px</span>
                </div>
              </div>

              {/* Icon Description */}
              <div className="bg-purple-50 rounded-lg p-4 text-sm text-gray-700">
                <h3 className="font-semibold mb-2">Design Elements:</h3>
                <ul className="space-y-1 text-xs">
                  <li>🌾 Wheat stalks representing agriculture</li>
                  <li>🛒 Shopping cart symbolizing marketplace</li>
                  <li>↔️ Connection arrow showing buyer-seller exchange</li>
                  <li>U Subtle "U" letterform for UDX branding</li>
                </ul>
              </div>
            </Card>
          </div>

          {/* Controls */}
          <div className="space-y-6">
            {/* Color Customization */}
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Palette className="w-5 h-5" />
                Customize Color
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Primary Color
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-20 h-12 rounded-lg cursor-pointer border-2 border-gray-300"
                    />
                    <input
                      type="text"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={copyColorCode}
                      className="h-12 w-12"
                    >
                      {copied ? (
                        <Check className="w-4 h-4 text-green-600" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-3">
                    Preset Colors
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {presetColors.map((preset) => (
                      <button
                        key={preset.color}
                        onClick={() => setPrimaryColor(preset.color)}
                        className={`p-3 rounded-lg border-2 transition-all ${
                          primaryColor === preset.color
                            ? 'border-purple-500 shadow-md'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div
                          className="w-full h-8 rounded mb-1"
                          style={{ background: preset.color }}
                        />
                        <span className="text-xs text-gray-600 block text-center">
                          {preset.name}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </Card>

            {/* Download Options */}
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Download className="w-5 h-5" />
                Download
              </h2>
              
              <div className="space-y-3">
                <Button
                  onClick={downloadSVG}
                  className="w-full bg-purple-600 hover:bg-purple-700"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download SVG (Vector)
                </Button>

                <div className="border-t pt-3">
                  <p className="text-sm text-gray-600 mb-3">
                    PNG Export (Raster):
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant="outline"
                      onClick={() => downloadPNG(512)}
                      className="text-sm"
                    >
                      512×512
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => downloadPNG(256)}
                      className="text-sm"
                    >
                      256×256
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => downloadPNG(128)}
                      className="text-sm"
                    >
                      128×128
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => downloadPNG(64)}
                      className="text-sm"
                    >
                      64×64
                    </Button>
                  </div>
                </div>
              </div>
            </Card>

            {/* Usage Guidelines */}
            <Card className="p-6 bg-gradient-to-br from-purple-50 to-white">
              <h2 className="text-xl font-semibold mb-4">Usage Guidelines</h2>
              
              <div className="space-y-3 text-sm text-gray-700">
                <div>
                  <h3 className="font-semibold mb-1">For Web:</h3>
                  <p className="text-xs">
                    Use SVG for best quality. Add to your HTML as favicon or app icon.
                  </p>
                </div>
                
                <div>
                  <h3 className="font-semibold mb-1">For Mobile Apps:</h3>
                  <p className="text-xs">
                    Use PNG format. iOS requires multiple sizes (60px, 120px, 180px).
                    Android recommends 512×512 for Play Store.
                  </p>
                </div>
                
                <div>
                  <h3 className="font-semibold mb-1">For Social Media:</h3>
                  <p className="text-xs">
                    Use 512×512 PNG for profile pictures and sharing previews.
                  </p>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mt-4">
                  <p className="text-xs text-yellow-800">
                    💡 <strong>Pro tip:</strong> The icon works best on light backgrounds. 
                    For dark mode, consider a lighter variant or add a subtle glow effect.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
