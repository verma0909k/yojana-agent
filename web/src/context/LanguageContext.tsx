import React, { createContext, useContext, useState, useEffect } from 'react';
import { auth } from '../auth';

type Language = 'en' | 'hi';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, defaultEn?: string) => string;
}

const translations: Record<string, Record<Language, string>> = {
  // Navigation
  'nav.home': { en: 'Home', hi: 'होम' },
  'nav.schemes': { en: 'Schemes', hi: 'योजनाएं' },
  'nav.documents': { en: 'Documents', hi: 'दस्तावेज़' },
  'nav.alerts': { en: 'Alerts', hi: 'सूचनाएं' },
  'nav.tracker': { en: 'Tracker', hi: 'ट्रैकर' },
  'nav.updates': { en: 'Updates', hi: 'बदलाव' },
  'nav.account': { en: 'Account', hi: 'खाता' },
  'nav.privacy': { en: 'Privacy & Settings', hi: 'गोपनीयता और सेटिंग्स' },
  'nav.logout': { en: 'Log out', hi: 'लॉग आउट' },

  // Header & App
  'app.name': { en: 'YojanaAgent', hi: 'योजना एजेंट' },
  'app.tagline': { en: 'Find every scheme you deserve', hi: 'हर सरकारी योजना जो आपके लिए है' },
  'app.gov_badge': { en: 'Official Scheme Assistant', hi: 'आधिकारिक योजना सहायक' },

  // Auth
  'auth.login_title': { en: 'Welcome back', hi: 'वापसी पर स्वागत है' },
  'auth.mobile_label': { en: 'Mobile Number', hi: 'मोबाइल नंबर' },
  'auth.send_otp': { en: 'Send OTP', hi: 'ओटीपी भेजें' },
  'auth.or': { en: 'or', hi: 'या' },
  'auth.google': { en: 'Continue with Google', hi: 'Google से जारी रखें' },
  'auth.email': { en: 'Continue with email', hi: 'ईमेल से जारी रखें' },
  'auth.demo_btn': { en: 'Try demo account', hi: 'डेमो खाते से आज़माएं' },
  'auth.aadhaar_note': { en: 'We never ask for your Aadhaar number to log in', hi: 'हम लॉगिन के लिए कभी आपका आधार नंबर नहीं मांगते' },
  'auth.new_here': { en: 'New here? Create account', hi: 'नए हैं? खाता बनाएं' },
  'auth.privacy_link': { en: 'Privacy Policy', hi: 'गोपनीयता नीति' },
  'auth.invalid_phone': { en: 'Please enter a valid 10-digit mobile number', hi: 'कृपया 10 अंकों का मान्य मोबाइल नंबर दर्ज करें' },
  'auth.too_many_attempts': { en: 'Too many attempts. Please try again after 5 minutes.', hi: 'बहुत अधिक प्रयास। कृपया 5 मिनट बाद प्रयास करें।' },

  // OTP
  'otp.enter_code': { en: 'Enter the 6-digit code sent to', hi: '6 अंकों का कोड दर्ज करें जो भेजा गया है' },
  'otp.change_number': { en: 'Change mobile number', hi: 'मोबाइल नंबर बदलें' },
  'otp.resend_in': { en: 'Resend OTP in', hi: 'ओटीपी पुनः भेजें' },
  'otp.resend_now': { en: 'Resend OTP', hi: 'ओटीपी पुनः भेजें' },
  'otp.wrong_code': { en: 'Invalid OTP code. Try 123456 for demo.', hi: 'अमान्य कोड। डेमो के लिए 123456 दर्ज करें।' },
  'otp.expired': { en: 'OTP has expired. Please request a new code.', hi: 'ओटीपी समाप्त हो गया है। कृपया नया कोड मांगें।' },
  'otp.verifying': { en: 'Verifying code...', hi: 'कोड की पुष्टि हो रही है...' },

  // Signup
  'signup.title': { en: 'Create your YojanaAgent account', hi: 'अपना योजना एजेंट खाता बनाएं' },
  'signup.step1': { en: 'Basic Details', hi: 'मूल विवरण' },
  'signup.step2': { en: 'Plain-Language Consent', hi: 'सहज भाषा में सहमति' },
  'signup.step3': { en: 'Welcome & Next Steps', hi: 'स्वागत और अगले कदम' },
  'signup.name_label': { en: 'Full Name', hi: 'पूरा नाम' },
  'signup.consent_storage': { en: 'Store my documents securely', hi: 'मेरे दस्तावेज़ सुरक्षित रूप से रखें' },
  'signup.consent_storage_desc': { en: 'Enables auto-prefilling applications and document health alerts.', hi: 'दस्तावेजों की मियाद नज़र रखने और आवेदन भरने में मदद करता है।' },
  'signup.consent_reminders': { en: 'Send reminders by email / Telegram / SMS', hi: 'ईमेल / टेलीग्राम / एसएमएस पर सूचना भेजें' },
  'signup.consent_reminders_desc': { en: 'We will notify you before deadlines and scheme expiry.', hi: 'अंतिम तिथि समाप्त होने से पहले आपको अलर्ट भेजा जाएगा।' },
  'signup.agree_terms': { en: 'I agree to the Terms of Service and Privacy Policy', hi: 'मैं नियम व शर्तों और गोपनीयता नीति से सहमत हूँ' },
  'signup.next': { en: 'Continue', hi: 'आगे बढ़ें' },
  'signup.describe_choice': { en: 'Describe my situation', hi: 'अपनी स्थिति बोलकर या लिखकर बताएं' },
  'signup.upload_choice': { en: 'Upload a document', hi: 'दस्तावेज़ की फोटो अपलोड करें' },

  // Intake & Home
  'home.describe_label': { en: 'Describe your situation', hi: 'अपनी स्थिति बताएं' },
  'home.describe_placeholder': { en: 'e.g. I am a small farmer in UP with 2 acres of land and family income ₹1.5L. What schemes can I get?', hi: 'जैसे: मैं यूपी में 2 एकड़ का किसान हूँ, परिवार की आय 1.5 लाख है। मुझे कौन सी योजना मिलेगी?' },
  'home.find_schemes': { en: 'Find my schemes', hi: 'योजनाएं खोजें' },
  'home.voice_listening': { en: 'Listening... Speak in Hindi or English', hi: 'सुन रहे हैं... हिंदी या अंग्रेज़ी में बोलें' },
  'home.personas_title': { en: 'One-tap demo personas:', hi: 'एक क्लिक डेमो प्रोफ़ाइल:' },
  'home.persona_farmer': { en: 'Farmer', hi: 'किसान' },
  'home.persona_student': { en: 'Student', hi: 'विद्यार्थी' },
  'home.persona_woman': { en: 'Woman Entrepreneur', hi: 'महिला उद्यमी' },
  'home.persona_senior': { en: 'Senior Citizen', hi: 'वरिष्ठ नागरिक' },
  'home.facts_title': { en: 'Facts we know about you', hi: 'आपके बारे में दर्ज तथ्य' },
  'home.reset_profile': { en: 'Reset profile', hi: 'प्रोफ़ाइल रीसेट करें' },
  'home.onboarding_title': { en: 'Quick Onboarding Checklist', hi: 'त्वरित शुरुआत चेकलिस्ट' },

  // Trace
  'trace.title': { en: 'Live Agent Execution Trace', hi: 'लाइव एआई एजेंट कार्यप्रणाली' },
  'trace.llm_active': { en: 'LLM Brain: Active', hi: 'एआई ब्रेन: सक्रिय' },
  'trace.view_results': { en: 'View eligible schemes', hi: 'पात्र योजनाएं देखें' },

  // Schemes & Results
  'schemes.eligible_title': { en: 'You are eligible for', hi: 'आप इन योजनाओं के लिए पात्र हैं' },
  'schemes.almost_title': { en: 'Almost eligible (Missing 1-2 facts)', hi: 'लगभग पात्र (1-2 विवरण शेष)' },
  'schemes.prepare_btn': { en: 'Prepare application', hi: 'आवेदन तैयार करें' },
  'schemes.why_qualify': { en: 'Why you qualify', hi: 'आप क्यों पात्र हैं' },
  'schemes.portal_verified': { en: 'Official Portal Verified', hi: 'सरकारी पोर्टल सत्यापित' },
  'schemes.needs_review': { en: 'Please double-check', hi: 'कृपया दोबारा जांचें' },
  'schemes.explain_why_not': { en: 'Explain why not', hi: 'कारण समझें (अपात्र क्यों)' },

  // Documents
  'docs.title': { en: 'Document Vault', hi: 'दस्तावेज़ वॉल्ट' },
  'docs.upload_drag': { en: 'Drag and drop document photo or click to browse', hi: 'दस्तावेज़ की फोटो यहाँ खींचें या चुनने के लिए क्लिक करें' },
  'docs.health_link': { en: 'View Document Health & Renewal Guide', hi: 'दस्तावेज़ नवीनीकरण स्वास्थ्य जांचें' },
  'docs.consistency_warn': { en: 'Document Consistency Warning', hi: 'दस्तावेज़ विसंगति चेतावनी' },

  // Tracker
  'tracker.title': { en: 'Application Lifecycle Tracker', hi: 'आवेदन प्रगति ट्रैकर' },
  'tracker.prefilled_pdf': { en: 'Download Pre-filled PDF', hi: 'भरा हुआ आवेदन फॉर्म डाउनलोड करें' },
  'tracker.calendar_ics': { en: 'Add .ics Reminder', hi: 'कैलेंडर में जोड़ें (.ics)' },

  // Alerts
  'alerts.title': { en: 'Alerts & AI Drafts', hi: 'अलर्ट और एआई संदेश ड्राफ्ट' },
  'alerts.drafts_tab': { en: 'Prepared Messages', hi: 'स्वीकृति योग्य संदेश' },
  'alerts.disclaimer': { en: 'Nothing is sent without your approval.', hi: 'आपकी अनुमति के बिना कोई संदेश नहीं भेजा जाता।' },
  'alerts.approve_send': { en: 'Approve & Send', hi: 'अनुमोदित करें और भेजें' },
};

const LanguageContext = createContext<LanguageContextType>({
  language: 'en',
  setLanguage: () => {},
  t: (k: string, d?: string) => d || k,
});

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const user = auth.getCurrentUser();
    return (user?.language as Language) || 'en';
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    auth.updateUser({ language: lang });
  };

  const t = (key: string, defaultEn?: string): string => {
    const entry = translations[key];
    if (entry && entry[language]) {
      return entry[language];
    }
    return defaultEn || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
