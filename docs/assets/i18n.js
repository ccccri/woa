// Minimal i18n: elements with data-i18n="key" get their text from STRINGS[lang][key].
// Pages may also contain blocks with lang="en" / lang="it" that are shown or hidden.
(function () {
  const STRINGS = {
    en: {
      tagline: "Wake your computer with Alexa. Free, open source, forever.",
      setupTitle: "Set up your computers",
      signInIntro: "Sign in with the same Amazon account you use with Alexa.",
      signIn: "Sign in with Amazon",
      signOut: "Sign out",
      yourComputers: "Your computers",
      noComputers: "No computers yet. Add one below.",
      addTitle: "Add a computer",
      nameLabel: "Name for Alexa (e.g. \"computer\" or \"office PC\")",
      macLabel: "MAC address of the wired network card",
      add: "Add",
      remove: "Remove",
      linked: "Alexa skill linked",
      notLinked: "Alexa skill not linked yet",
      notLinkedHelp: "Enable the WOA skill in the Alexa app and link your account. Your computers are saved here in the meantime.",
      added: "Added. Alexa already knows about it: try \"Alexa, turn on {name}\".",
      addedDiscover: "Added. Now say \"Alexa, discover devices\".",
      removed: "Removed.",
      removedDiscover: "Removed. If Alexa still shows it, delete it in the Alexa app.",
      confirmRemove: "Remove \"{name}\"?",
      deleteAll: "Delete all my data",
      confirmDeleteAll: "Delete all your computers and data stored by WOA?",
      deletedAll: "All your data was deleted.",
      genericError: "Something went wrong. Please try again.",
      sessionExpired: "Your session expired. Please sign in again.",
      notConfigured: "This page is not configured yet (config.js).",
      macHelpTitle: "How to find the MAC address",
      requirementsTitle: "Before you start",
    },
    it: {
      tagline: "Accendi il computer con Alexa. Gratis, open source, per sempre.",
      setupTitle: "Configura i tuoi computer",
      signInIntro: "Accedi con lo stesso account Amazon che usi con Alexa.",
      signIn: "Accedi con Amazon",
      signOut: "Esci",
      yourComputers: "I tuoi computer",
      noComputers: "Nessun computer. Aggiungine uno qui sotto.",
      addTitle: "Aggiungi un computer",
      nameLabel: "Nome per Alexa (es. \"computer\" o \"PC ufficio\")",
      macLabel: "Indirizzo MAC della scheda di rete cablata",
      add: "Aggiungi",
      remove: "Rimuovi",
      linked: "Skill Alexa collegata",
      notLinked: "Skill Alexa non ancora collegata",
      notLinkedHelp: "Attiva la skill WOA nell'app Alexa e collega l'account. Intanto i tuoi computer restano salvati qui.",
      added: "Aggiunto. Alexa lo conosce già: prova \"Alexa, accendi {name}\".",
      addedDiscover: "Aggiunto. Ora di' \"Alexa, cerca dispositivi\".",
      removed: "Rimosso.",
      removedDiscover: "Rimosso. Se Alexa lo mostra ancora, eliminalo dall'app Alexa.",
      confirmRemove: "Rimuovere \"{name}\"?",
      deleteAll: "Elimina tutti i miei dati",
      confirmDeleteAll: "Eliminare tutti i tuoi computer e i dati salvati da WOA?",
      deletedAll: "Tutti i tuoi dati sono stati eliminati.",
      genericError: "Qualcosa è andato storto. Riprova.",
      sessionExpired: "Sessione scaduta. Accedi di nuovo.",
      notConfigured: "Questa pagina non è ancora configurata (config.js).",
      macHelpTitle: "Come trovare l'indirizzo MAC",
      requirementsTitle: "Prima di iniziare",
    },
  };

  function detect() {
    const saved = localStorage.getItem("woa-lang");
    if (saved && STRINGS[saved]) return saved;
    return (navigator.language || "en").toLowerCase().startsWith("it") ? "it" : "en";
  }

  let lang = detect();

  function t(key, vars) {
    let s = (STRINGS[lang] && STRINGS[lang][key]) || STRINGS.en[key] || key;
    for (const [k, v] of Object.entries(vars || {})) s = s.replace(`{${k}}`, v);
    return s;
  }

  function apply() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("main [lang]").forEach((el) => { el.hidden = el.lang !== lang; });
    document.querySelectorAll("nav.lang button").forEach((b) => {
      b.classList.toggle("active", b.dataset.lang === lang);
    });
  }

  function set(newLang) {
    lang = newLang;
    localStorage.setItem("woa-lang", lang);
    apply();
    document.dispatchEvent(new CustomEvent("woa-lang"));
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("nav.lang button").forEach((b) => {
      b.addEventListener("click", () => set(b.dataset.lang));
    });
    apply();
  });

  window.WOA_I18N = { t, set, get lang() { return lang; } };
})();
