import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../api';
import { ExtractedFact } from '../types';
import {
  Mic,
  MicOff,
  Upload,
  Sparkles,
  ArrowRight,
  User,
  RotateCcw,
  CheckCircle,
  Circle,
  Edit2,
  Check,
  Shield,
  FileCheck
} from 'lucide-react';

const DEMO_PERSONAS = [
  {
    id: 'farmer',
    labelKey: 'home.persona_farmer',
    defaultLabel: 'Farmer',
    icon: '🌾',
    textEn: 'I am a small farmer in Uttar Pradesh with 2.5 acres of agricultural land and an annual family income of ₹1,40,000. I need financial assistance and crop security.',
    textHi: 'मैं उत्तर प्रदेश का एक छोटा किसान हूँ, मेरे पास 2.5 एकड़ कृषि भूमि है और वार्षिक पारिवारिक आय ₹1,40,000 है। मुझे आर्थिक सहायता और फसल सुरक्षा चाहिए।',
    facts: [
      { id: 'f1', field: 'Occupation', value: 'Farmer', confidence: 0.98, source: 'self-reported' as const },
      { id: 'f2', field: 'State', value: 'Uttar Pradesh', confidence: 0.95, source: 'self-reported' as const },
      { id: 'f3', field: 'Land Holding', value: '2.5 Acres', confidence: 0.92, source: 'self-reported' as const },
      { id: 'f4', field: 'Family Income', value: '₹1,40,000 / yr', confidence: 0.94, source: 'self-reported' as const },
      { id: 'f5', field: 'Caste Category', value: 'OBC', confidence: 0.88, source: 'self-reported' as const },
    ],
  },
  {
    id: 'student',
    labelKey: 'home.persona_student',
    defaultLabel: 'Student',
    icon: '🎓',
    textEn: 'I am a 19-year-old girl pursuing B.Tech in Haryana. My family annual income is ₹1,80,000. Looking for government merit and higher education scholarships.',
    textHi: 'मैं हरियाणा में बी.टेक कर रही 19 वर्षीय छात्रा हूँ। मेरे परिवार की वार्षिक आय ₹1,80,000 है। मुझे उच्च शिक्षा के लिए छात्रवृत्ति की आवश्यकता है।',
    facts: [
      { id: 'f1', field: 'Occupation', value: 'Student (Undergraduate)', confidence: 0.99, source: 'from document' as const },
      { id: 'f2', field: 'Gender', value: 'Female', confidence: 0.99, source: 'from document' as const },
      { id: 'f3', field: 'State', value: 'Haryana', confidence: 0.96, source: 'from document' as const },
      { id: 'f4', field: 'Family Income', value: '₹1,80,000 / yr', confidence: 0.97, source: 'from document' as const },
      { id: 'f5', field: 'Age', value: '19 Years', confidence: 0.99, source: 'from document' as const },
    ],
  },
  {
    id: 'woman',
    labelKey: 'home.persona_woman',
    defaultLabel: 'Woman Entrepreneur',
    icon: '💼',
    textEn: 'I run a small handloom stitching unit in Jaipur, Rajasthan with 3 local women. Looking for zero-collateral business expansion loans and subsidies.',
    textHi: 'मैं जयपुर राजस्थान में 3 महिलाओं के साथ एक छोटा सिलाई केंद्र चलाती हूँ। मुझे व्यवसाय विस्तार के लिए बिना गारंटी वाला ऋण चाहिए।',
    facts: [
      { id: 'f1', field: 'Occupation', value: 'Micro-entrepreneur (Textiles)', confidence: 0.95, source: 'self-reported' as const },
      { id: 'f2', field: 'Gender', value: 'Female', confidence: 0.99, source: 'self-reported' as const },
      { id: 'f3', field: 'State', value: 'Rajasthan', confidence: 0.95, source: 'self-reported' as const },
      { id: 'f4', field: 'Family Income', value: '₹2,10,000 / yr', confidence: 0.91, source: 'self-reported' as const },
      { id: 'f5', field: 'Enterprise Type', value: 'Micro Enterprise', confidence: 0.94, source: 'self-reported' as const },
    ],
  },
  {
    id: 'senior',
    labelKey: 'home.persona_senior',
    defaultLabel: 'Senior Citizen',
    icon: '👴',
    textEn: 'I am a 68-year-old retired informal worker living in rural Bihar. No pension. Need health insurance coverage and monthly old-age financial support.',
    textHi: 'मैं बिहार के ग्रामीण क्षेत्र का 68 वर्षीय नागरिक हूँ। कोई पेंशन नहीं है। मुझे स्वास्थ्य बीमा और मासिक वृद्धावस्था सहायता चाहिए।',
    facts: [
      { id: 'f1', field: 'Age', value: '68 Years', confidence: 0.99, source: 'from document' as const },
      { id: 'f2', field: 'State', value: 'Bihar', confidence: 0.97, source: 'from document' as const },
      { id: 'f3', field: 'Occupation', value: 'Senior / Retired', confidence: 0.95, source: 'self-reported' as const },
      { id: 'f4', field: 'Family Income', value: '₹75,000 / yr', confidence: 0.92, source: 'from document' as const },
      { id: 'f5', field: 'BPL Status', value: 'Eligible (SECC)', confidence: 0.93, source: 'from document' as const },
    ],
  },
];

export const Home: React.FC = () => {
  const { t, language } = useLanguage();
  const navigate = useNavigate();

  const [query, setQuery] = useState(
    language === 'hi'
      ? 'मैं हरियाणा में बी.टेक कर रही 19 वर्षीय छात्रा हूँ। मेरे परिवार की वार्षिक आय ₹1,80,000 है। मुझे छात्रवृत्ति की आवश्यकता है।'
      : 'I am a 19-year-old female student pursuing B.Tech in Haryana with family income ₹1,80,000. Looking for central and state scholarships.'
  );

  const [isRecording, setIsRecording] = useState(false);
  const [activePersona, setActivePersona] = useState<string>('student');

  // Facts panel state
  const [facts, setFacts] = useState<ExtractedFact[]>([
    { id: 'f1', field: 'Occupation', value: 'Student (Engineering)', confidence: 0.98, source: 'from document' },
    { id: 'f2', field: 'Gender', value: 'Female', confidence: 0.99, source: 'from document' },
    { id: 'f3', field: 'State', value: 'Haryana', confidence: 0.95, source: 'from document' },
    { id: 'f4', field: 'Family Income', value: '₹1,80,000 / yr', confidence: 0.96, source: 'from document' },
    { id: 'f5', field: 'Age', value: '19 Years', confidence: 0.99, source: 'from document' },
    { id: 'f6', field: 'Caste Category', value: 'General / EWS', confidence: 0.89, source: 'self-reported' },
  ]);

  const [editingFactId, setEditingFactId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  // Onboarding checklist items
  const [checklist, setChecklist] = useState({
    describedSituation: true,
    uploadedDocument: true,
    enabledReminders: false,
  });

  const handleSelectPersona = (persona: (typeof DEMO_PERSONAS)[0]) => {
    setActivePersona(persona.id);
    setQuery(language === 'hi' ? persona.textHi : persona.textEn);
    setFacts(persona.facts);
  };

  const handleVoiceToggle = () => {
    if (!isRecording) {
      setIsRecording(true);
      // Simulate real speech recognition with timer
      setTimeout(() => {
        setIsRecording(false);
        if (language === 'hi') {
          setQuery('मुझे लघु उद्योग शुरू करने के लिए मुद्रा योजना और सरकारी सहायता चाहिए।');
        } else {
          setQuery('I want to start a micro dairy farming unit in Punjab. What central government grants and loans are available?');
        }
      }, 3500);
    } else {
      setIsRecording(false);
    }
  };

  const handleStartFactEdit = (fact: ExtractedFact) => {
    setEditingFactId(fact.id);
    setEditValue(fact.value);
  };

  const handleSaveFact = (id: string) => {
    setFacts(facts.map((f) => (f.id === id ? { ...f, value: editValue, source: 'self-reported' } : f)));
    setEditingFactId(null);
  };

  const handleResetProfile = () => {
    setFacts([]);
    setQuery('');
    setActivePersona('');
  };

  const handleFindSchemes = () => {
    // Navigate to live agent trace execution
    navigate('/trace', { state: { query, facts } });
  };

  return (
    <div className="space-y-6">
      {/* Onboarding Checklist for Users */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-saffron-500" />
            <h2 className="font-bold text-slate-900 text-base">
              {t('home.onboarding_title')}
            </h2>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-orange-100 text-saffron-800 rounded-full">
            {language === 'hi' ? '2/3 पूर्ण' : '2 of 3 Completed'}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
            <CheckCircle className="w-5 h-5 text-gov-green shrink-0" />
            <span className="text-xs font-medium text-slate-700">
              {language === 'hi' ? '१. अपनी स्थिति का विवरण दें' : '1. Describe situation'}
            </span>
          </div>

          <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
            <CheckCircle className="w-5 h-5 text-gov-green shrink-0" />
            <span className="text-xs font-medium text-slate-700">
              {language === 'hi' ? '२. आय / आधार प्रमाण जोड़ें' : '2. Identity document linked'}
            </span>
          </div>

          <div
            onClick={() => navigate('/alerts')}
            className="flex items-center gap-2.5 p-2.5 rounded-xl bg-orange-50/60 border border-saffron-200 cursor-pointer hover:bg-orange-50 transition"
          >
            <Circle className="w-5 h-5 text-saffron-500 shrink-0" />
            <span className="text-xs font-medium text-saffron-900">
              {language === 'hi' ? '३. समय पर सूचनाएं चालू करें' : '3. Enable deadline alerts'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Intake Box + Facts Side Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Intake & Persona Selection */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-5">
          <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200/80 shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <label htmlFor="intake-query" className="font-bold text-slate-900 text-lg sm:text-xl">
                {t('home.describe_label')}
              </label>
              <span className="text-xs text-slate-500 font-medium hidden sm:inline">
                {language === 'hi' ? 'हिंदी व अंग्रेज़ी दोनों मान्य' : 'Multilingual voice & text'}
              </span>
            </div>

            <p className="text-sm text-slate-500 mb-4">
              {language === 'hi'
                ? 'अपनी आय, पेशा, ज़मीन, उम्र और ज़रूरत बताएं। हमारा AI नियम पुस्तिका से सटीक योजनाएं खोजेगा।'
                : 'State your occupation, family income, landholding, state, and specific needs.'}
            </p>

            {/* Large Text Area */}
            <div className="relative">
              <textarea
                id="intake-query"
                rows={4}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('home.describe_placeholder')}
                className="w-full p-4 text-base border border-slate-300 rounded-xl focus:ring-2 focus:ring-saffron-500 focus:border-transparent transition leading-relaxed resize-none text-slate-800"
              />

              {/* Voice recording overlay */}
              {isRecording && (
                <div className="absolute inset-0 bg-white/95 rounded-xl border border-saffron-400 flex flex-col items-center justify-center gap-2 p-4 animate-pulse">
                  <div className="w-12 h-12 rounded-full bg-red-500 text-white flex items-center justify-center shadow-lg shadow-red-500/30">
                    <Mic className="w-6 h-6 animate-bounce" />
                  </div>
                  <span className="font-semibold text-slate-900 text-sm">
                    {t('home.voice_listening')}
                  </span>
                  <span className="text-xs text-slate-500">
                    {language === 'hi' ? 'कृपया अपनी स्थिति बताएं...' : 'Listening to speech in real time...'}
                  </span>
                </div>
              )}
            </div>

            {/* Action Buttons Row */}
            <div className="flex flex-wrap items-center justify-between gap-3 mt-4 pt-3 border-t border-slate-100">
              <div className="flex items-center gap-2">
                {/* Voice button */}
                <button
                  type="button"
                  onClick={handleVoiceToggle}
                  className={`min-h-[44px] px-3.5 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 transition ${
                    isRecording
                      ? 'bg-red-500 text-white'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                  title="Speak in your language"
                >
                  {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4 text-saffron-600" />}
                  <span>{isRecording ? (language === 'hi' ? 'रोकें' : 'Stop') : (language === 'hi' ? 'बोलकर बताएं' : 'Voice')}</span>
                </button>

                {/* Upload document photo */}
                <button
                  type="button"
                  onClick={() => navigate('/documents')}
                  className="min-h-[44px] px-3.5 py-2 rounded-xl text-sm font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center gap-2 transition"
                >
                  <Upload className="w-4 h-4 text-slate-600" />
                  <span>{language === 'hi' ? 'दस्तावेज़ फोटो' : 'Upload Document'}</span>
                </button>
              </div>

              {/* Primary action */}
              <button
                type="button"
                onClick={handleFindSchemes}
                disabled={!query.trim()}
                className="min-h-[48px] px-6 py-2.5 bg-saffron-500 hover:bg-saffron-600 disabled:opacity-50 text-white font-bold rounded-xl text-base shadow-md shadow-saffron-500/20 flex items-center gap-2 transition"
              >
                <span>{t('home.find_schemes')}</span>
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Persona Chips Section */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
            <div className="text-sm font-bold text-slate-900 mb-3 flex items-center justify-between">
              <span>{t('home.personas_title')}</span>
              <span className="text-xs text-slate-500 font-normal">
                {language === 'hi' ? 'एक क्लिक में आज़माएं' : 'Tap to simulate persona'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {DEMO_PERSONAS.map((p) => {
                const isSelected = activePersona === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handleSelectPersona(p)}
                    className={`min-h-[44px] p-3 rounded-xl border text-left transition flex items-center gap-2.5 ${
                      isSelected
                        ? 'border-saffron-500 bg-orange-50/70 text-saffron-900 ring-2 ring-saffron-500/20 font-bold'
                        : 'border-slate-200 hover:border-slate-300 text-slate-700 bg-slate-50/40'
                    }`}
                  >
                    <span className="text-xl shrink-0">{p.icon}</span>
                    <span className="text-xs sm:text-sm leading-tight truncate">
                      {t(p.labelKey, p.defaultLabel)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: "Facts we know about you" side panel */}
        <div className="lg:col-span-5 xl:col-span-4">
          <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs sticky top-20">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <User className="w-5 h-5 text-saffron-600" />
                <h3 className="font-bold text-slate-900 text-base">
                  {t('home.facts_title')}
                </h3>
              </div>
              <button
                type="button"
                onClick={handleResetProfile}
                className="text-xs text-slate-500 hover:text-red-600 flex items-center gap-1 font-medium transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>{t('home.reset_profile')}</span>
              </button>
            </div>

            <p className="text-xs text-slate-500 mb-4 leading-relaxed">
              {language === 'hi'
                ? 'ये तथ्य आपके अपलोड किए गए दस्तावेजों और बयानों से निकाले गए हैं। किसी भी तथ्य पर क्लिक कर संपादित करें।'
                : 'Facts extracted from verified documents & self-reports. Tap any fact to edit.'}
            </p>

            {/* Fact list */}
            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {facts.length === 0 ? (
                <div className="p-6 text-center text-sm text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  {language === 'hi' ? 'कोई तथ्य दर्ज नहीं है। कृपया स्थिति बताएं।' : 'No profile facts extracted yet. Type or pick a persona.'}
                </div>
              ) : (
                facts.map((fact) => {
                  const isEditing = editingFactId === fact.id;
                  const isDoc = fact.source === 'from document';

                  return (
                    <div
                      key={fact.id}
                      className="p-3 rounded-xl border border-slate-200 bg-slate-50/60 hover:bg-white hover:border-slate-300 transition"
                    >
                      <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                        <span className="font-semibold text-slate-700">{fact.field}</span>
                        <div className="flex items-center gap-1.5">
                          {/* Confidence badge */}
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-green-50 text-gov-green border border-green-200">
                            {Math.round(fact.confidence * 100)}%
                          </span>
                          {/* Source tag */}
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold flex items-center gap-0.5 ${
                              isDoc
                                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                : 'bg-slate-100 text-slate-600 border border-slate-200'
                            }`}
                          >
                            {isDoc && <FileCheck className="w-2.5 h-2.5" />}
                            {isDoc ? 'Doc' : 'Self'}
                          </span>
                        </div>
                      </div>

                      {/* Value and Edit */}
                      {isEditing ? (
                        <div className="flex items-center gap-2 mt-1">
                          <input
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="w-full px-2 py-1 text-sm border border-saffron-500 rounded-md focus:outline-none"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={() => handleSaveFact(fact.id)}
                            className="p-1 bg-saffron-500 text-white rounded-md hover:bg-saffron-600"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between mt-1">
                          <span className="font-bold text-slate-900 text-sm">{fact.value}</span>
                          <button
                            type="button"
                            onClick={() => handleStartFactEdit(fact)}
                            className="p-1 text-slate-400 hover:text-slate-700 rounded transition"
                            title="Edit this fact"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Bottom guarantee */}
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-500">
              <Shield className="w-4 h-4 text-gov-green shrink-0" />
              <span>{language === 'hi' ? 'आधार/आय डेटा सुरक्षित वॉल्ट में है' : 'Vault storage certified under MeitY guidelines'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
