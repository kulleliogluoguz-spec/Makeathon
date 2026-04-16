# PROMPT: Add Platform Language Toggle (TR / EN)

## CRITICAL RULES
- Do NOT rewrite any existing file completely
- Do NOT push to git
- Do NOT touch backend — this is frontend-only

## WHAT THIS DOES

A language toggle in Settings (Turkish / English) that switches the ENTIRE platform UI language. Stored in localStorage so it persists across sessions.

## IMPLEMENTATION

### New file: `frontend/src/lib/i18n.js`

```javascript
const translations = {
  en: {
    // Navbar
    nav_personas: "Personas",
    nav_agents: "Agents",
    nav_customers: "Customers",
    nav_conversations: "Conversations",
    nav_analytics: "Analytics",
    nav_settings: "Settings",

    // Personas
    personas_title: "Personas",
    personas_create: "Create Persona",
    personas_template_title: "Create a Persona",
    personas_template_subtitle: "Start from a template or create from scratch",
    personas_from_scratch: "or start from scratch →",
    personas_editor_identity: "Identity",
    personas_editor_personality: "Personality Traits",
    personas_editor_communication: "Communication Style",
    personas_editor_phrases: "Phrases",
    personas_editor_response_rules: "Response Rules",
    personas_editor_emotional: "Emotional Intelligence",
    personas_editor_escalation: "Escalation Rules",
    personas_editor_safety: "Safety & Boundaries",
    personas_editor_custom: "Custom Instructions",
    personas_editor_system_prompt: "Generated System Prompt",
    personas_editor_voice: "Voice",
    personas_editor_voice_desc: "Choose an ElevenLabs voice for your agent",
    personas_editor_catalogs: "Product Catalogs",
    personas_editor_catalogs_desc: "Upload product catalogs so the AI can recommend products during conversations.",
    personas_save: "Save Changes",
    personas_generate_prompt: "Generate from Settings",
    personas_discard: "Discard Changes",

    // Agents
    agents_title: "Agents",
    agents_create: "Create Agent",

    // Customers
    customers_title: "Customers",
    customers_subtitle: "Unified customer database across all channels",
    customers_add: "+ Add Customer",
    customers_search_name: "Search by name...",
    customers_search_phone: "Phone number...",
    customers_search_email: "Email or @handle...",
    customers_all_channels: "All channels",
    customers_all_categories: "All categories",
    customers_active: "Active",
    customers_archived: "Archived",
    customers_all: "All",
    customers_detail: "Customer Details",
    customers_display_name: "Display name",
    customers_handle: "Handle / Username",
    customers_email: "Email",
    customers_phone: "Phone",
    customers_tags: "Tags",
    customers_notes: "Notes",
    customers_conversations: "Conversations",
    customers_save: "Save",
    customers_delete: "Delete",
    customers_archive: "Archive",
    customers_unarchive: "Unarchive",
    customers_no_customers: "No customers yet. They will appear here when they message you, or you can add them manually.",
    customers_add_title: "Add Customer",
    customers_source: "Source",
    customers_create: "Create",
    customers_cancel: "Cancel",
    customers_messages: "messages",

    // Conversations
    conversations_title: "Conversations",
    conversations_subtitle: "Live view of all customer conversations with intent scoring",
    conversations_search: "Search inside messages... (e.g. price, return, t-shirt)",
    conversations_search_btn: "Search",
    conversations_clear: "Clear",
    conversations_no_conversations: "No conversations yet. When customers DM your Instagram, they will appear here.",
    conversations_select: "Select a conversation to view details",
    conversations_details: "Details",
    conversations_intent_score: "INTENT SCORE",
    conversations_signals: "SIGNALS",
    conversations_next_action: "NEXT ACTION",
    conversations_conversation: "CONVERSATION",
    conversations_export_pdf: "Export PDF",
    conversations_customer: "CUSTOMER",
    conversations_ai: "AI",
    conversations_found: "Found",
    conversations_in: "in",
    conversations_conversations: "conversation(s)",
    conversations_matches: "match(es)",

    // Analytics
    analytics_title: "Analytics",
    analytics_subtitle: "Performance overview across all channels",
    analytics_today: "Today",
    analytics_week: "Week",
    analytics_month: "Month",
    analytics_all_time: "All Time",
    analytics_conversations: "Conversations",
    analytics_customers: "Customers",
    analytics_messages: "Messages",
    analytics_avg_intent: "Avg Intent Score",
    analytics_high_intent: "High Intent (70+)",
    analytics_ready_to_buy: "Ready to buy",
    analytics_active_today: "Active Today",
    analytics_channel_dist: "Channel Distribution",
    analytics_intent_dist: "Intent Score Distribution",
    analytics_sales_funnel: "Sales Funnel",
    analytics_categories: "Categories",
    analytics_daily_volume: "Daily Conversation Volume (Last 30 Days)",
    analytics_top_products: "Top Mentioned Products",
    analytics_no_data: "No data",
    analytics_no_products: "No product mentions yet",
    analytics_mentions: "mentions",

    // Settings
    settings_title: "Settings",
    settings_subtitle: "Business hours, auto-reply, and archive settings",
    settings_working_hours: "Working Hours",
    settings_active: "Active",
    settings_disabled_247: "Disabled (24/7)",
    settings_timezone: "TIMEZONE",
    settings_outside_hours: "Outside Hours Auto-Reply",
    settings_enabled: "Enabled",
    settings_holidays: "Holidays",
    settings_holiday_add: "Add",
    settings_auto_archive: "Auto-Archive",
    settings_auto_archive_desc: "Automatically archive customers with no activity after this many hours. Set 0 to disable.",
    settings_hours_inactivity: "hours of inactivity",
    settings_save: "Save Settings",
    settings_saving: "Saving...",
    settings_saved: "✓ Saved!",
    settings_livechat: "Live Chat Widget",
    settings_livechat_desc: "Add this code to any website to enable AI chat. Paste before the closing </body> tag.",
    settings_persona: "PERSONA",
    settings_select_persona: "Select persona...",
    settings_copy_code: "Copy Code",
    settings_copied: "✓ Copied!",
    settings_test_widget: "Test on This Page",
    settings_language: "Platform Language",
    settings_language_desc: "Change the language of the entire platform interface.",

    // Common
    common_select: "Select",
    common_preview: "Preview",
    common_selected: "Selected",
    common_upload: "Upload",
    common_delete: "Delete",
    common_edit: "Edit",
    common_close: "Close",
    common_loading: "Loading...",
    common_no_data: "No data",
  },

  tr: {
    // Navbar
    nav_personas: "Personalar",
    nav_agents: "Ajanlar",
    nav_customers: "Müşteriler",
    nav_conversations: "Konuşmalar",
    nav_analytics: "Analitik",
    nav_settings: "Ayarlar",

    // Personas
    personas_title: "Personalar",
    personas_create: "Persona Oluştur",
    personas_template_title: "Persona Oluştur",
    personas_template_subtitle: "Bir şablondan başla veya sıfırdan oluştur",
    personas_from_scratch: "veya sıfırdan başla →",
    personas_editor_identity: "Kimlik",
    personas_editor_personality: "Kişilik Özellikleri",
    personas_editor_communication: "İletişim Stili",
    personas_editor_phrases: "İfadeler",
    personas_editor_response_rules: "Yanıt Kuralları",
    personas_editor_emotional: "Duygusal Zeka",
    personas_editor_escalation: "Yönlendirme Kuralları",
    personas_editor_safety: "Güvenlik & Sınırlar",
    personas_editor_custom: "Özel Talimatlar",
    personas_editor_system_prompt: "Oluşturulan System Prompt",
    personas_editor_voice: "Ses",
    personas_editor_voice_desc: "Ajınız için bir ElevenLabs sesi seçin",
    personas_editor_catalogs: "Ürün Katalogları",
    personas_editor_catalogs_desc: "AI'ın konuşmalarda ürün önerebilmesi için katalog yükleyin.",
    personas_save: "Değişiklikleri Kaydet",
    personas_generate_prompt: "Ayarlardan Oluştur",
    personas_discard: "Değişiklikleri İptal Et",

    // Agents
    agents_title: "Ajanlar",
    agents_create: "Ajan Oluştur",

    // Customers
    customers_title: "Müşteriler",
    customers_subtitle: "Tüm kanallardaki birleşik müşteri veritabanı",
    customers_add: "+ Müşteri Ekle",
    customers_search_name: "İsimle ara...",
    customers_search_phone: "Telefon numarası...",
    customers_search_email: "E-posta veya @kullanıcıadı...",
    customers_all_channels: "Tüm kanallar",
    customers_all_categories: "Tüm kategoriler",
    customers_active: "Aktif",
    customers_archived: "Arşivlenmiş",
    customers_all: "Tümü",
    customers_detail: "Müşteri Detayları",
    customers_display_name: "Görünen ad",
    customers_handle: "Kullanıcı adı",
    customers_email: "E-posta",
    customers_phone: "Telefon",
    customers_tags: "Etiketler",
    customers_notes: "Notlar",
    customers_conversations: "Konuşmalar",
    customers_save: "Kaydet",
    customers_delete: "Sil",
    customers_archive: "Arşivle",
    customers_unarchive: "Arşivden Çıkar",
    customers_no_customers: "Henüz müşteri yok. Mesaj attıklarında burada görünecekler veya elle ekleyebilirsiniz.",
    customers_add_title: "Müşteri Ekle",
    customers_source: "Kaynak",
    customers_create: "Oluştur",
    customers_cancel: "İptal",
    customers_messages: "mesaj",

    // Conversations
    conversations_title: "Konuşmalar",
    conversations_subtitle: "Tüm müşteri konuşmalarının canlı görünümü ve niyet puanlaması",
    conversations_search: "Mesajlarda ara... (ör. fiyat, iade, tişört)",
    conversations_search_btn: "Ara",
    conversations_clear: "Temizle",
    conversations_no_conversations: "Henüz konuşma yok. Müşteriler Instagram'dan mesaj attığında burada görünecek.",
    conversations_select: "Detayları görmek için bir konuşma seçin",
    conversations_details: "Detaylar",
    conversations_intent_score: "NİYET PUANI",
    conversations_signals: "SİNYALLER",
    conversations_next_action: "SONRAKİ ADIM",
    conversations_conversation: "KONUŞMA",
    conversations_export_pdf: "PDF İndir",
    conversations_customer: "MÜŞTERİ",
    conversations_ai: "YAPAY ZEKA",
    conversations_found: "Bulundu",
    conversations_in: "",
    conversations_conversations: "konuşmada",
    conversations_matches: "eşleşme",

    // Analytics
    analytics_title: "Analitik",
    analytics_subtitle: "Tüm kanallardaki performans özeti",
    analytics_today: "Bugün",
    analytics_week: "Hafta",
    analytics_month: "Ay",
    analytics_all_time: "Tüm Zamanlar",
    analytics_conversations: "Konuşmalar",
    analytics_customers: "Müşteriler",
    analytics_messages: "Mesajlar",
    analytics_avg_intent: "Ort. Niyet Puanı",
    analytics_high_intent: "Yüksek Niyet (70+)",
    analytics_ready_to_buy: "Satın almaya hazır",
    analytics_active_today: "Bugün Aktif",
    analytics_channel_dist: "Kanal Dağılımı",
    analytics_intent_dist: "Niyet Puanı Dağılımı",
    analytics_sales_funnel: "Satış Hunisi",
    analytics_categories: "Kategoriler",
    analytics_daily_volume: "Günlük Konuşma Hacmi (Son 30 Gün)",
    analytics_top_products: "En Çok Bahsedilen Ürünler",
    analytics_no_data: "Veri yok",
    analytics_no_products: "Henüz ürün bahsi yok",
    analytics_mentions: "bahis",

    // Settings
    settings_title: "Ayarlar",
    settings_subtitle: "Çalışma saatleri, otomatik yanıt ve arşiv ayarları",
    settings_working_hours: "Çalışma Saatleri",
    settings_active: "Aktif",
    settings_disabled_247: "Devre Dışı (7/24)",
    settings_timezone: "SAAT DİLİMİ",
    settings_outside_hours: "Mesai Dışı Otomatik Yanıt",
    settings_enabled: "Açık",
    settings_holidays: "Tatil Günleri",
    settings_holiday_add: "Ekle",
    settings_auto_archive: "Otomatik Arşivleme",
    settings_auto_archive_desc: "Bu kadar saat hareketsiz kalan müşterileri otomatik arşivle. Devre dışı bırakmak için 0 girin.",
    settings_hours_inactivity: "saat hareketsizlik",
    settings_save: "Ayarları Kaydet",
    settings_saving: "Kaydediliyor...",
    settings_saved: "✓ Kaydedildi!",
    settings_livechat: "Canlı Sohbet Widget'ı",
    settings_livechat_desc: "Bu kodu herhangi bir web sitesine ekleyerek AI sohbeti etkinleştirin. </body> etiketinden önce yapıştırın.",
    settings_persona: "PERSONA",
    settings_select_persona: "Persona seçin...",
    settings_copy_code: "Kodu Kopyala",
    settings_copied: "✓ Kopyalandı!",
    settings_test_widget: "Bu Sayfada Test Et",
    settings_language: "Platform Dili",
    settings_language_desc: "Tüm platform arayüzünün dilini değiştirin.",

    // Common
    common_select: "Seç",
    common_preview: "Önizle",
    common_selected: "Seçildi",
    common_upload: "Yükle",
    common_delete: "Sil",
    common_edit: "Düzenle",
    common_close: "Kapat",
    common_loading: "Yükleniyor...",
    common_no_data: "Veri yok",
  },
};


let currentLang = localStorage.getItem('platform_language') || 'en';

export function t(key) {
  return translations[currentLang]?.[key] || translations['en']?.[key] || key;
}

export function getLang() {
  return currentLang;
}

export function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('platform_language', lang);
  window.location.reload();
}
```

### Edit: `frontend/src/pages/SettingsPage.jsx`

Add the language toggle section. At the top, add import:
```jsx
import { t, getLang, setLang } from '../lib/i18n';
```

Add this section at the very TOP of the settings sections (BEFORE Working Hours):

```jsx
{/* Platform Language */}
<section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
  <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.5rem' }}>{t('settings_language')}</h2>
  <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>{t('settings_language_desc')}</p>
  <div style={{ display: 'flex', gap: '0.5rem' }}>
    <button
      onClick={() => setLang('en')}
      style={{
        padding: '8px 24px', fontSize: '0.875rem', borderRadius: '9999px',
        background: getLang() === 'en' ? '#000' : '#fff',
        color: getLang() === 'en' ? '#fff' : '#374151',
        border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500,
      }}
    >English</button>
    <button
      onClick={() => setLang('tr')}
      style={{
        padding: '8px 24px', fontSize: '0.875rem', borderRadius: '9999px',
        background: getLang() === 'tr' ? '#000' : '#fff',
        color: getLang() === 'tr' ? '#fff' : '#374151',
        border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500,
      }}
    >Türkçe</button>
  </div>
</section>
```

### IMPORTANT — How to use translations in existing pages:

The i18n.js file provides a `t()` function. To translate a page, import it and replace hardcoded strings:

```jsx
import { t } from '../lib/i18n';

// Before:
<h1>Customers</h1>

// After:
<h1>{t('customers_title')}</h1>
```

Apply this to ALL existing pages. For each page, replace hardcoded English text with `t('key')` calls using the keys from translations above.

Pages to update (add `import { t } from '../lib/i18n';` at top of each, then replace strings):

1. **App.jsx** — navbar links
2. **PersonaListPage.jsx** — title, create button, template modal
3. **PersonaEditorPage.jsx** — section headings, buttons
4. **CustomersPage.jsx** — title, subtitle, filter labels, buttons, detail labels
5. **ConversationsPage.jsx** — title, subtitle, search, detail labels
6. **AnalyticsPage.jsx** — title, subtitle, card labels, chart titles
7. **SettingsPage.jsx** — section titles, labels, buttons

For EACH page: only replace the hardcoded text strings with t() calls. Do NOT change any logic, layout, styling, or component structure.

Example for App.jsx navbar:
```jsx
// Before:
<Link to="/customers">Customers</Link>
// After:
<Link to="/customers">{t('nav_customers')}</Link>
```

Example for CustomersPage:
```jsx
// Before:
<h1>Customers</h1>
<p>Unified customer database across all channels</p>
// After:
<h1>{t('customers_title')}</h1>
<p>{t('customers_subtitle')}</p>
```

Do this for EVERY visible text string in EVERY page. Use the translation keys provided in the i18n.js file.

## DO NOT
- ❌ DO NOT change any logic or layout
- ❌ DO NOT restructure components
- ❌ DO NOT touch backend
- ❌ DO NOT push to git

## TEST

1. Open Settings → see language toggle at top → click "Türkçe" → page reloads → entire UI is in Turkish
2. Navigate to every page — all text should be Turkish
3. Go back to Settings → click "English" → everything back to English
4. Close browser, reopen → language choice persists (localStorage)

## START NOW
