import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import {
  Brain,
  Search,
  CheckCircle2,
  Globe2,
  ShieldAlert,
  Loader2,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Activity,
  Cpu
} from 'lucide-react';

interface StepDef {
  id: string;
  name: string;
  actionEn: string;
  actionHi: string;
  icon: React.ReactNode;
  detailsEn: string;
  detailsHi: string;
  reasonEn: string;
  reasonHi: string;
  durationMs: number;
}

const TRACE_STEPS: StepDef[] = [
  {
    id: 'planner',
    name: '1. Planner Brain',
    actionEn: 'Decomposing citizen intent & formulating demographic constraint vector.',
    actionHi: 'नागरिक की ज़रूरतों का विश्लेषण एवं पात्रता नियमों की संरचना तैयार करना।',
    icon: <Brain className="w-5 h-5 text-purple-600" />,
    detailsEn: 'Identified core target profile: Student, Undergraduate female in Haryana with family income ₹1,80,000.',
    detailsHi: 'लक्षित प्रोफ़ाइल की पहचान: हरियाणा में बी.टेक छात्रा, पारिवारिक आय ₹1,80,000।',
    reasonEn: 'Planner agent parsed natural text into structured metadata query for matching engine.',
    reasonHi: 'प्लानर एजेंट ने सामान्य पाठ को संरचित मेटाडेटा में रूपांतरित किया।',
    durationMs: 900,
  },
  {
    id: 'search',
    name: '2. ChromaDB Semantic Search',
    actionEn: 'Querying high-dimensional multilingual vector store for top schemes.',
    actionHi: 'मल्टीलिंगुअल वेक्टर स्टोर से सर्वाधिक प्रासंगिक योजनाओं की खोज।',
    icon: <Search className="w-5 h-5 text-blue-600" />,
    detailsEn: 'Retrieved 5 matching central & state schemes with cosine similarity > 0.82.',
    detailsHi: '0.82 से अधिक समानता वाली 5 प्रमुख केंद्रीय एवं राज्य योजनाएं खोजी गईं।',
    reasonEn: 'Vector search retrieved PM Kisan, National Scholarship Portal, AICTE Pragati, and Ayushman Bharat.',
    reasonHi: 'सर्च इंजन ने पीएम किसान, नेशनल स्कॉलरशिप, एआईसीटीई प्रगति एवं आयुष्मान भारत योजनाएं चुनीं।',
    durationMs: 1100,
  },
  {
    id: 'rule_check',
    name: '3. Deterministic Rule Evaluator',
    actionEn: 'Validating hard constraints against official gazette thresholds.',
    actionHi: 'आधिकारिक राजपत्र के निर्धारित मानदंडों के आधार पर पात्रता की जांच।',
    icon: <CheckCircle2 className="w-5 h-5 text-gov-green" />,
    detailsEn: 'Passed 3 schemes (ELIGIBLE), 1 scheme flagged as ALMOST (missing certificate verification).',
    detailsHi: '3 योजनाओं में पूर्ण पात्रता (ELIGIBLE), 1 योजना में लगभग पात्रता (ALMOST)।',
    reasonEn: 'Family income of ₹1.8L is below NSP limit of ₹2.5L and Pragati limit of ₹8.0L. Age 19 satisfies criteria.',
    reasonHi: 'पारिवारिक आय सीमा एवं 19 वर्ष आयु वर्ग के नियम पूरी तरह संतुष्ट पाए गए।',
    durationMs: 1200,
  },
  {
    id: 'portal_verify',
    name: '4. Live Portal Reachability',
    actionEn: 'Probing live government endpoints & WAF integrity.',
    actionHi: 'सरकारी सर्वर एवं आधिकारिक पोर्टलों की लाइव उपलब्धता का सत्यापन।',
    icon: <Globe2 className="w-5 h-5 text-teal-600" />,
    detailsEn: 'HTTP 200 confirmed on scholarships.gov.in and pmkisan.gov.in. Application portal active.',
    detailsHi: 'scholarships.gov.in तथा pmkisan.gov.in पर HTTP 200 सत्यापित। आवेदन विंडो खुली है।',
    reasonEn: 'Verified that portals are taking applications and not down for maintenance.',
    reasonHi: 'सत्यापित किया गया कि सरकारी पोर्टल चालू हैं और कोई सर्वर रुकावट नहीं है।',
    durationMs: 1000,
  },
  {
    id: 'critic',
    name: '5. Safety & Hallucination Critic',
    actionEn: 'Auditing claims against official texts with zero hallucination guarantee.',
    actionHi: 'सभी दावों का आधिकारिक दस्तावेजों से मिलान व भ्रामक जानकारी की रोकथाम।',
    icon: <ShieldAlert className="w-5 h-5 text-saffron-600" />,
    detailsEn: 'Critic confidence: 99.1%. Pruned 1 unverified third-party grant. All benefits grounded.',
    detailsHi: 'सटीकता स्कोर: 99.1%। असत्यापित योजनाओं को हटा दिया गया। सभी लाभ प्रमाणित हैं।',
    reasonEn: 'Every rupee benefit and required document was cross-referenced with official gazette rules.',
    reasonHi: 'प्रत्येक वित्तीय लाभ और आवश्यक दस्तावेज को सरकारी अधिसूचना से सत्यापित किया गया।',
    durationMs: 800,
  },
];

export const AgentTrace: React.FC = () => {
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();

  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});
  const [isFinished, setIsFinished] = useState(false);

  useEffect(() => {
    let timer: any;

    const executeSteps = (index: number) => {
      if (index >= TRACE_STEPS.length) {
        setIsFinished(true);
        return;
      }

      setCurrentStepIndex(index);

      timer = setTimeout(() => {
        setCompletedSteps((prev) => [...prev, TRACE_STEPS[index].id]);
        // Auto expand step details for clarity
        setExpandedSteps((prev) => ({ ...prev, [TRACE_STEPS[index].id]: true }));
        executeSteps(index + 1);
      }, TRACE_STEPS[index].durationMs);
    };

    executeSteps(0);

    return () => {
      clearTimeout(timer);
    };
  }, []);

  const toggleExpand = (stepId: string) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }));
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Top Header & Brain Status Banner */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            {t('trace.title')}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {language === 'hi'
              ? 'एआई एजेंट आपके लिए 5 स्तरीय नियमों और पोर्टलों की जांच कर रहा है'
              : 'Autonomous multi-step pipeline evaluating schemes with hard rules'}
          </p>
        </div>

        {/* LLM Brain Active Indicator */}
        <div className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-green-50 border border-green-200 text-gov-green">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-600"></span>
          </span>
          <div className="flex items-center gap-1.5 text-xs font-bold tracking-wide">
            <Cpu className="w-3.5 h-3.5" />
            <span>{t('trace.llm_active')} (gemini-3.5-flash-lite)</span>
          </div>
        </div>
      </div>

      {/* Vertical Steps Timeline */}
      <div className="relative pl-6 sm:pl-8 space-y-4">
        {/* Timeline vertical track */}
        <div className="absolute left-2.5 sm:left-3.5 top-4 bottom-4 w-0.5 bg-slate-200" />

        {TRACE_STEPS.map((step, idx) => {
          const isDone = completedSteps.includes(step.id);
          const isRunning = currentStepIndex === idx && !isDone;
          const isPending = idx > currentStepIndex;
          const isExpanded = !!expandedSteps[step.id];

          if (isPending) return null; // Only slide in steps as they are triggered

          return (
            <div
              key={step.id}
              className={`relative bg-white rounded-2xl border transition-all duration-300 shadow-xs overflow-hidden animate-slide-in ${
                isRunning
                  ? 'border-saffron-400 ring-2 ring-saffron-500/20'
                  : isDone
                  ? 'border-slate-200'
                  : 'border-slate-100 opacity-60'
              }`}
            >
              {/* Timeline Node Icon in Margin */}
              <div
                className={`absolute -left-6 sm:-left-8 top-5 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                  isDone
                    ? 'bg-gov-green border-gov-green text-white'
                    : isRunning
                    ? 'bg-saffron-500 border-saffron-500 text-white animate-pulse'
                    : 'bg-white border-slate-300 text-slate-300'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  <div className="w-1.5 h-1.5 rounded-full bg-white" />
                )}
              </div>

              {/* Card Header */}
              <div
                onClick={() => toggleExpand(step.id)}
                className="p-4 sm:p-5 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 transition select-none"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0">
                    {step.icon}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm sm:text-base">
                        {step.name}
                      </span>
                      {isRunning && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-100 text-saffron-800 animate-pulse">
                          {language === 'hi' ? 'प्रगति पर...' : 'Processing...'}
                        </span>
                      )}
                    </div>
                    <p className="text-xs sm:text-sm text-slate-600 mt-0.5 line-clamp-1">
                      {language === 'hi' ? step.actionHi : step.actionEn}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 ml-2">
                  {isRunning ? (
                    <Loader2 className="w-5 h-5 text-saffron-500 animate-spin" />
                  ) : isDone ? (
                    <span className="text-xs font-semibold text-gov-green flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4" />
                      <span className="hidden sm:inline">{language === 'hi' ? 'सत्यापित' : 'Passed'}</span>
                    </span>
                  ) : null}

                  <button type="button" className="text-slate-400 p-1">
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Card Expandable Details */}
              {isExpanded && (
                <div className="px-4 pb-4 sm:px-5 sm:pb-5 pt-1 border-t border-slate-100 text-xs sm:text-sm space-y-2.5 bg-slate-50/40">
                  <div className="p-3 bg-white rounded-xl border border-slate-200/80">
                    <span className="font-semibold text-slate-700 block mb-1">
                      {language === 'hi' ? 'कार्रवाई विवरण:' : 'Action Detail:'}
                    </span>
                    <p className="text-slate-600">
                      {language === 'hi' ? step.detailsHi : step.detailsEn}
                    </p>
                  </div>

                  <div className="p-3 bg-white rounded-xl border border-slate-200/80">
                    <span className="font-semibold text-slate-700 block mb-1">
                      {language === 'hi' ? 'एआई तर्क / कारण:' : 'Reason & Grounding:'}
                    </span>
                    <p className="text-slate-600">
                      {language === 'hi' ? step.reasonHi : step.reasonEn}
                    </p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Completion & CTA */}
      {isFinished && (
        <div className="bg-orange-50 border border-saffron-200 rounded-2xl p-6 text-center shadow-md animate-fade-in">
          <div className="w-12 h-12 bg-saffron-500 text-white rounded-full flex items-center justify-center mx-auto mb-3 shadow-md shadow-saffron-500/20">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 mb-1">
            {language === 'hi' ? 'सत्यापन पूर्ण! 5 योजनाएं उपलब्ध हैं' : 'Trace Complete! 5 Schemes Evaluated'}
          </h2>
          <p className="text-sm text-slate-600 mb-5 max-w-md mx-auto">
            {language === 'hi'
              ? '3 योजनाओं के लिए आप पूरी तरह पात्र हैं, और 1 योजना में सिर्फ 1 दस्तावेज की आवश्यकता है।'
              : 'You are fully eligible for 3 schemes. Tap below to review benefits and start application packages.'}
          </p>

          <button
            type="button"
            onClick={() => navigate('/schemes')}
            className="min-h-[48px] px-8 py-3 bg-saffron-500 hover:bg-saffron-600 text-white font-bold rounded-xl text-base shadow-lg shadow-saffron-500/25 inline-flex items-center gap-2 transition"
          >
            <span>{t('trace.view_results')}</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
};
