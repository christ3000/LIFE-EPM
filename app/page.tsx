"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  ArrowRight, CalendarDays, Check, Download,
  ChevronDown, Church, CircleHelp, FileText, Heart, LayoutDashboard, LogOut, MapPin,
  Menu, MessageCircle, Plus, Search, Send, Settings, ShieldCheck, Users, Wallet, X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

type Role = "super_admin" | "secretary" | "treasurer" | "shepherd";
type User = { id: number; username: string; full_name: string; role: Role; must_change_password: boolean; is_active?: boolean };
type ChurchIdentity = { name: string; denomination: string; initials: string; city: string; logo_url?: string | null };
type AttendanceMember = { id: number; first_name: string; last_name: string; church_number: string };
type StoryFilter = "all" | "prayer" | "testimony";
type Section = "dashboard" | "fideles" | "cultes" | "finances" | "budgets" | "prieres" | "familles" | "parametres" | "utilisateurs" | "sms";
type RecordRow = Record<string, string | number | boolean | null>;
type DashboardData = {
  church?: ChurchIdentity;
  total_members?: number;
  new_members_this_month?: number;
  open_prayer_requests?: number;
  birthdays_today?: { id: number; name: string }[];
  upcoming_service?: RecordRow | null;
  upcoming_program?: RecordRow | null;
  total_services?: number;
  total_programs?: number;
  total_presence?: number;
  total_absences?: number;
  marriages_count?: number;
  births_count?: number;
  finance_month?: RecordRow;
  finance_year?: RecordRow;
};
type SummaryData = Record<string, number | string>;
type FinancialTab = "operations" | "budgets";
type ServiceGroup = "culte" | "programme";
type SettingsTab = "identity" | "zones" | "users" | "certificates";
type BibleVerse = { reference: string; text: string };
type MessagingRecipient = { id: number; full_name: string; role: Role };
type SmsRecipient = { id: number; name: string; phone: string };
type ConversationSummary = {
  id: number;
  title: string;
  is_group: boolean;
  participants: string[];
  last_message: string;
  last_sender: string | null;
  updated_at: string;
  unread_count: number;
};
type ChatMessage = { id: number; sender_id: number; sender_name: string; body: string; created_at: string };

// Laissez cette URL vide pour que Next.js transmette les appels /api au backend.
const API = process.env.NEXT_PUBLIC_API_URL ?? "";

// Conserve le statut HTTP pour afficher des erreurs API utiles dans l'interface.
class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}
const navigationGroups: { label: string; items: { id: Section; label: string; icon: LucideIcon }[] }[] = [
  { label: "Espace principal", items: [
    { id: "dashboard", label: "Tableau de bord", icon: LayoutDashboard },
    { id: "fideles", label: "Fidèles", icon: Users },
    { id: "cultes", label: "Cultes & programmes", icon: CalendarDays },
  ] },
  { label: "Vie de l'église", items: [
    { id: "prieres", label: "Prières & témoignages", icon: Heart },
    { id: "familles", label: "Mariages & naissances", icon: Church },
    { id: "sms", label: "Messagerie", icon: MessageCircle },
  ] },
  { label: "Administration", items: [
    { id: "finances", label: "Finances & budgets", icon: Wallet },
    { id: "parametres", label: "Paramètres", icon: Settings },
    { id: "utilisateurs", label: "Utilisateurs & rôles", icon: ShieldCheck },
  ] },
];
const labels: Record<Section, string> = {
  dashboard: "Tableau de bord", fideles: "Fidèles", cultes: "Cultes & programmes",
  finances: "Finances", budgets: "Budgets", prieres: "Prières & témoignages",
  familles: "Mariages & naissances",
  parametres: "Paramètres", utilisateurs: "Utilisateurs & rôles", sms: "Messagerie",
};

// Sélection locale de versets de la Louis Segond 1910, traduction du domaine public.
const bibleVerses: BibleVerse[] = [
  { reference: "Philippiens 4:13", text: "Je puis tout par celui qui me fortifie." },
  { reference: "Psaumes 23:1", text: "L'Éternel est mon berger: je ne manquerai de rien." },
  { reference: "Matthieu 11:28", text: "Venez à moi, vous tous qui êtes fatigués et chargés, et je vous donnerai du repos." },
  { reference: "Proverbes 3:5", text: "Confie-toi en l'Éternel de tout ton coeur, Et ne t'appuie pas sur ta sagesse;" },
  { reference: "Ésaïe 41:10", text: "Ne crains rien, car je suis avec toi; Ne promène pas des regards inquiets, car je suis ton Dieu; Je te fortifie, je viens à ton secours, Je te soutiens de ma droite triomphante." },
  { reference: "Psaumes 46:1", text: "Dieu est pour nous un refuge et un appui, Un secours qui ne manque jamais dans la détresse." },
  { reference: "Ésaïe 40:31", text: "Mais ceux qui se confient en l'Éternel renouvellent leur force. Ils prennent le vol comme les aigles; Ils courent, et ne se lassent point, Ils marchent, et ne se fatiguent point." },
  { reference: "Philippiens 4:6", text: "Ne vous inquiétez de rien; mais en toute chose faites connaître vos besoins à Dieu par des prières et des supplications, avec des actions de grâces." },
  { reference: "Psaumes 119:105", text: "Ta parole est une lampe à mes pieds, Et une lumière sur mon sentier." },
  { reference: "Jean 14:27", text: "Je vous laisse la paix, je vous donne ma paix. Je ne vous donne pas comme le monde donne. Que votre coeur ne se trouble point, et ne s'alarme point." },
  { reference: "Josué 1:9", text: "Fortifie-toi et prends courage. Ne t'effraie point et ne t'épouvante point, car l'Éternel, ton Dieu, est avec toi dans tout ce que tu entreprendras." },
  { reference: "Psaumes 121:1-2", text: "Je lève mes yeux vers les montagnes... D'où me viendra le secours? Le secours me vient de l'Éternel, Qui a fait les cieux et la terre." },
  { reference: "Proverbes 16:3", text: "Recommande à l'Éternel tes oeuvres, Et tes projets réussiront." },
  { reference: "Matthieu 6:33", text: "Cherchez premièrement le royaume et la justice de Dieu; et toutes ces choses vous seront données par-dessus." },
  { reference: "Psaumes 27:1", text: "L'Éternel est ma lumière et mon salut: De qui aurais-je crainte? L'Éternel est le soutien de ma vie: De qui aurais-je peur?" },
];
const BIBLE_VERSE_STORAGE_KEY = "life-epm-last-bible-verse";

// Restaure le dernier verset affiché lorsqu'une session déjà ouverte est retrouvée.
function savedBibleVerse(): BibleVerse {
  try {
    const storedIndex = window.localStorage.getItem(BIBLE_VERSE_STORAGE_KEY);
    const index = storedIndex === null ? -1 : Number(storedIndex);
    if (Number.isInteger(index) && index >= 0 && index < bibleVerses.length) return bibleVerses[index];
  } catch (error) {
    console.warn("Le dernier verset n'a pas pu être lu depuis le stockage local.", error);
  }
  return bibleVerses[0];
}

// Choisit un autre verset à chaque connexion et mémorise son index dans ce navigateur.
function nextBibleVerse(current?: BibleVerse): BibleVerse {
  const indicesToAvoid = new Set<number>();
  const currentIndex = current ? bibleVerses.findIndex((verse) => verse.reference === current.reference) : -1;
  if (currentIndex >= 0) indicesToAvoid.add(currentIndex);
  try {
    const storedValue = window.localStorage.getItem(BIBLE_VERSE_STORAGE_KEY);
    if (storedValue !== null) {
      const storedIndex = Number(storedValue);
      if (Number.isInteger(storedIndex) && storedIndex >= 0 && storedIndex < bibleVerses.length) {
        indicesToAvoid.add(storedIndex);
      }
    }
  } catch (error) {
    console.warn("Le dernier verset n'a pas pu être lu depuis le stockage local.", error);
  }

  const availableIndices = bibleVerses.map((_, index) => index).filter((index) => !indicesToAvoid.has(index));
  const selectedIndex = availableIndices[Math.floor(Math.random() * availableIndices.length)];
  try {
    window.localStorage.setItem(BIBLE_VERSE_STORAGE_KEY, String(selectedIndex));
  } catch (error) {
    console.warn("Le dernier verset n'a pas pu être mémorisé dans le stockage local.", error);
  }
  return bibleVerses[selectedIndex];
}

// Lit les liens directs du README : ?page=... avec un onglet facultatif.
function readPageLocation() {
  const params = new URLSearchParams(window.location.search);
  const page = params.get("page");
  return {
    section: page && Object.prototype.hasOwnProperty.call(labels, page) ? page as Section : "dashboard" as Section,
    serviceGroup: params.get("group") === "programme" ? "programme" as ServiceGroup : "culte" as ServiceGroup,
    financialTab: params.get("tab") === "budgets" ? "budgets" as FinancialTab : "operations" as FinancialTab,
    familyTab: params.get("tab") === "births" ? "births" as const : "marriages" as const,
    settingsTab: (["identity", "zones", "users", "certificates"].includes(params.get("tab") ?? "")
      ? params.get("tab")
      : "identity") as SettingsTab,
  };
}

// Met à jour l'adresse sans recharger la page, afin de partager un lien vers une rubrique.
function writePageLocation(section: Section, key?: "group" | "tab", value?: string) {
  const url = new URL(window.location.href);
  url.searchParams.set("page", section);
  url.searchParams.delete("group");
  url.searchParams.delete("tab");
  if (key && value) url.searchParams.set(key, value);
  window.history.replaceState(null, "", url);
}

// Remplace les valeurs absentes par un texte lisible avant affichage.
const text = (value: unknown) => value === null || value === undefined || value === "" ? "—" : typeof value === "boolean" ? value ? "Oui" : "Non" : String(value);

// Exporte uniquement les lignes déjà visibles et respecte les droits appliqués par l'API.
function exportRowsCsv(rows: RecordRow[], columns: string[], title: string) {
  const escapeCell = (value: unknown) => {
    let cell = value === null || value === undefined ? "" : String(value);
    if (/^\s*[=+\-@]/.test(cell)) cell = `'${cell}`;
    return `"${cell.replaceAll('"', '""')}"`;
  };
  const content = [
    columns.map((column) => escapeCell(columnLabel(column))).join(","),
    ...rows.map((row) => columns.map((column) => escapeCell(row[column])).join(",")),
  ].join("\r\n");
  const blob = new Blob(["\uFEFF", content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${title.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "").toLowerCase() || "life-epm"}.csv`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Centralise les appels API, l'envoi du cookie de session et le traitement des erreurs.
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = init?.body instanceof FormData
    ? { ...init.headers }
    : { "Content-Type": "application/json", ...init?.headers };
  const response = await fetch(`${API}/api${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? `La requête a échoué (${response.status}).`, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

// Point d'entrée : gère la session, les données des modules, la navigation et les formulaires.
export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [bibleVerse, setBibleVerse] = useState<BibleVerse>(bibleVerses[0]);
  const [church, setChurch] = useState<ChurchIdentity | null>(null);
  const [section, setSection] = useState<Section>("dashboard");
  const [serviceGroup, setServiceGroup] = useState<ServiceGroup>("culte");
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("identity");
  const [familyTab, setFamilyTab] = useState<"marriages" | "births">("marriages");
  const [financialTab, setFinancialTab] = useState<FinancialTab>("operations");
  const [storyFilter, setStoryFilter] = useState<StoryFilter>("all");
  const [records, setRecords] = useState<RecordRow[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData>({});
  const [search, setSearch] = useState("");
  const [loginName, setLoginName] = useState("pasteur.bobou");
  const [loginPassword, setLoginPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [modal, setModal] = useState(false);
  const [editingRecord, setEditingRecord] = useState<RecordRow | null>(null);
  const [familyChoiceOpen, setFamilyChoiceOpen] = useState(false);
  const [attendanceTarget, setAttendanceTarget] = useState<RecordRow | null>(null);
  const [attendanceMembers, setAttendanceMembers] = useState<AttendanceMember[]>([]);
  const [formMembers, setFormMembers] = useState<AttendanceMember[]>([]);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Charge les données de chaque écran ; vérifier ce bloc si un écran est vide ou obsolète.
  const loadSection = useCallback(async (
    selected: Section,
    filter = "",
    options?: { serviceGroup?: ServiceGroup; financialTab?: FinancialTab; familyTab?: "marriages" | "births"; settingsTab?: SettingsTab },
  ) => {
    const selectedServiceGroup = options?.serviceGroup ?? serviceGroup;
    const selectedFinancialTab = options?.financialTab ?? financialTab;
    const selectedFamilyTab = options?.familyTab ?? familyTab;
    if (selected === "dashboard") {
      const data = await api<DashboardData>("/dashboard");
      setDashboard(data);
      setChurch(data.church ?? null);
      setRecords([]);
      setSummary(null);
      return;
    }
    if (selected === "sms") {
      setRecords([]);
      return;
    }
    if (selected === "prieres") {
      const [prayers, testimonies] = await Promise.all([
        api<RecordRow[]>("/prayers"),
        api<RecordRow[]>("/testimonies"),
      ]);
      const combinedStories: RecordRow[] = [
        ...prayers.map((prayer) => ({ ...prayer, record_kind: "prayer" })),
        ...testimonies.map((testimony) => ({ ...testimony, record_kind: "testimony" })),
      ];
      combinedStories.sort((left, right) => new Date(String(right.created_at)).valueOf() - new Date(String(left.created_at)).valueOf());
      setRecords(combinedStories);
      setSummary(null);
      return;
    }
    if (selected === "parametres") {
      if (options?.settingsTab === "zones") setRecords(await api<RecordRow[]>("/zones"));
      else if (options?.settingsTab === "users") setRecords(await api<RecordRow[]>("/users"));
      else setRecords([]);
      setSummary(null);
      return;
    }
    if (selected === "fideles" || selected === "cultes") {
      const path = selected === "fideles"
        ? `/members${filter ? `?search=${encodeURIComponent(filter)}` : ""}`
        : `/services?group=${selectedServiceGroup}`;
      const summaryPath = selected === "fideles" ? "/members/summary" : "/services/summary";
      const selectedSummaryPath = selected === "cultes" ? `${summaryPath}?group=${selectedServiceGroup}` : summaryPath;
      const [data, metrics] = await Promise.all([
        api<RecordRow[]>(path),
        api<SummaryData>(selectedSummaryPath),
      ]);
      setRecords(data);
      setSummary(metrics);
      return;
    }
    if (selected === "finances") {
      const [data, metrics] = await Promise.all([
        api<RecordRow[]>(selectedFinancialTab === "budgets" ? "/budgets" : "/finances"),
        api<SummaryData>(`/financial-summary?year=${new Date().getFullYear()}`),
      ]);
      setRecords(data);
      setSummary(metrics);
      return;
    }
    const paths: Record<Exclude<Section, "dashboard" | "prieres" | "sms">, string> = {
      fideles: `/members${filter ? `?search=${encodeURIComponent(filter)}` : ""}`,
      cultes: "/services",
      finances: "/finances",
      budgets: "/budgets",
      familles: `/families/${selectedFamilyTab}`,
      parametres: "/zones",
      utilisateurs: "/users",
    };
    const data = await api<RecordRow[]>(paths[selected]);
    setRecords(data);
    setSummary(null);
  }, [familyTab, financialTab, serviceGroup]);

  const loadSectionRef = useRef(loadSection);
  useEffect(() => { loadSectionRef.current = loadSection; }, [loadSection]);

  // Restaure la session existante à l'ouverture de l'application.
  const initialize = useCallback(async () => {
    try {
      const authenticated = await api<User>("/auth/me");
      setUser(authenticated);
      if (!authenticated.must_change_password) {
        setBibleVerse(nextBibleVerse(savedBibleVerse()));
        const location = readPageLocation();
        setSection(location.section);
        setServiceGroup(location.serviceGroup);
        setFinancialTab(location.financialTab);
        setFamilyTab(location.familyTab);
        setSettingsTab(location.settingsTab);
        await loadSectionRef.current(location.section, "", location);
      }
    } catch (reason) {
      if (reason instanceof ApiError && reason.status !== 401) setError(reason.message);
      else if (!(reason instanceof ApiError)) setError("Impossible de joindre le serveur Life EPM.");
    }
  }, []);

  useEffect(() => { void initialize(); }, [initialize]);

  const visibleNavigationGroups = useMemo(() => navigationGroups.map((group) => ({
    ...group,
    items: group.items.filter((item) => {
      if (item.id === "finances") return user?.role === "super_admin" || user?.role === "treasurer";
      if (item.id === "utilisateurs" || item.id === "parametres") return user?.role === "super_admin";
      if (item.id === "familles") return user?.role === "super_admin" || user?.role === "secretary";
      return true;
    }),
  })).filter((group) => group.items.length > 0), [user]);

  // Encadre les actions : efface les anciens messages, affiche les erreurs et libère l'interface.
  async function runAction(action: () => Promise<void>) {
    setError("");
    setNotice("");
    setBusy(true);
    try { await action(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Une erreur inattendue s'est produite."); }
    finally { setBusy(false); }
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction(async () => {
      const authenticated = await api<User>("/auth/login", { method: "POST", body: JSON.stringify({ username: loginName, password: loginPassword }) });
      setUser(authenticated);
      if (!authenticated.must_change_password) {
        setBibleVerse(nextBibleVerse(bibleVerse));
        const location = readPageLocation();
        setSection(location.section);
        setServiceGroup(location.serviceGroup);
        setFinancialTab(location.financialTab);
        setFamilyTab(location.familyTab);
        setSettingsTab(location.settingsTab);
        await loadSection(location.section, "", location);
      }
    });
  }

  async function signOut() {
    await runAction(async () => {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      setLoginPassword("");
      setCurrentPassword("");
      setNewPassword("");
    });
  }

  async function selectSection(selected: Section) {
    setError("");
    setSection(selected);
    writePageLocation(selected);
    setMobileMenu(false);
    if (selected === "parametres") setSettingsTab("identity");
    if (selected === "cultes") setServiceGroup("culte");
    if (selected === "finances") setFinancialTab("operations");
    if (selected === "familles") setFamilyTab("marriages");
    const defaults = {
      serviceGroup: selected === "cultes" ? "culte" as const : serviceGroup,
      financialTab: selected === "finances" ? "operations" as const : financialTab,
      familyTab: selected === "familles" ? "marriages" as const : familyTab,
      settingsTab: selected === "parametres" ? "identity" as const : settingsTab,
    };
    await runAction(() => loadSection(selected, "", defaults));
  }

  async function selectServiceGroup(group: ServiceGroup) {
    setServiceGroup(group);
    writePageLocation("cultes", "group", group);
    await runAction(async () => {
      const [data, metrics] = await Promise.all([
        api<RecordRow[]>(`/services?group=${group}`),
        api<SummaryData>(`/services/summary?group=${group}`),
      ]);
      setRecords(data);
      setSummary(metrics);
    });
  }

  async function selectSettingsTab(tab: SettingsTab) {
    setSettingsTab(tab);
    writePageLocation("parametres", "tab", tab);
    if (tab === "zones") {
      await runAction(async () => setRecords(await api<RecordRow[]>("/zones")));
    } else if (tab === "users") {
      await runAction(async () => setRecords(await api<RecordRow[]>("/users")));
    } else {
      setRecords([]);
    }
  }

  async function openRecordModal() {
    setEditingRecord(null);
    if (section === "prieres" || section === "familles") setFormMembers(await api<AttendanceMember[]>("/members"));
    if (section === "familles") {
      setFamilyChoiceOpen(true);
      return;
    }
    setModal(true);
  }

  function openMemberEditor(record: RecordRow) {
    setEditingRecord(record);
    setModal(true);
  }

  async function chooseFamilyEntry(type: "marriages" | "births") {
    setFamilyChoiceOpen(false);
    setFamilyTab(type);
    writePageLocation("familles", "tab", type);
    await runAction(async () => {
      setRecords(await api<RecordRow[]>(`/families/${type}`));
      setModal(true);
    });
  }

  async function saveRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const body = Object.fromEntries([...formData.entries()].filter(([, value]) => value !== ""));
    const storyKind = section === "prieres" ? String(body.record_kind ?? "prayer") : "";
    delete body.record_kind;
    const configs: Partial<Record<Section, { path: string; method: string }>> = {
      fideles: { path: "/members", method: "POST" },
      cultes: { path: "/services", method: "POST" },
      finances: { path: financialTab === "budgets" ? "/budgets" : "/finances", method: "POST" },
      budgets: { path: "/budgets", method: "POST" },
      familles: { path: `/families/${familyTab}`, method: "POST" },
      parametres: { path: "/zones", method: "POST" },
      utilisateurs: { path: "/users", method: "POST" },
    };
    const config = editingRecord && section === "fideles"
      ? { path: `/members/${editingRecord.id}`, method: "PATCH" }
      : section === "prieres"
      ? { path: storyKind === "testimony" ? "/testimonies" : "/prayers", method: "POST" }
      : configs[section];
    if (!config) return;
    await runAction(async () => {
      await api(config.path, { method: config.method, body: JSON.stringify(body) });
      setModal(false);
      setEditingRecord(null);
      setNotice(editingRecord ? "Les informations du fidèle ont été mises à jour." : "Les informations ont été enregistrées.");
      await loadSection("dashboard");
      await loadSection(section, search);
    });
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction(async () => {
      const updated = await api<User>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      setUser(updated);
      setCurrentPassword("");
      setNewPassword("");
      setBibleVerse(nextBibleVerse(savedBibleVerse()));
      const location = readPageLocation();
      setSection(location.section);
      setServiceGroup(location.serviceGroup);
      setFinancialTab(location.financialTab);
      setFamilyTab(location.familyTab);
      setSettingsTab(location.settingsTab);
      await loadSection(location.section, "", location);
      setNotice("Votre nouveau mot de passe est enregistré.");
    });
  }

  async function saveChurchIdentity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const identity = Object.fromEntries(formData.entries());
    await runAction(async () => {
      const updated = await api<ChurchIdentity>("/church", { method: "PATCH", body: JSON.stringify(identity) });
      setChurch(updated);
      setNotice("L'identité de l'église a été mise à jour.");
    });
  }

  async function saveChurchLogo(file: File) {
    const formData = new FormData();
    formData.set("file", file);
    await runAction(async () => {
      const updated = await api<ChurchIdentity>("/church/logo", { method: "POST", body: formData });
      setChurch(updated);
      setNotice("Le logo de l'église a été mis à jour.");
    });
  }

  async function removeChurchLogo() {
    await runAction(async () => {
      await api("/church/logo", { method: "DELETE" });
      setChurch((previous) => previous ? { ...previous, logo_url: null } : previous);
      setNotice("Le logo de l'église a été supprimé.");
    });
  }

  async function openAttendance(row: RecordRow) {
    await runAction(async () => {
      setAttendanceMembers(await api<AttendanceMember[]>("/members"));
      setAttendanceTarget(row);
    });
  }

  async function saveAttendance(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const memberId = formData.get("member_id");
    const present = formData.get("present") === "true";
    if (!attendanceTarget || typeof memberId !== "string") return;
    await runAction(async () => {
      await api(`/services/${attendanceTarget.id}/attendance/${memberId}`, { method: "POST", body: JSON.stringify({ present }) });
      setAttendanceTarget(null);
      setNotice(present ? "La présence a été enregistrée." : "L'absence a été enregistrée.");
      await loadSection("cultes");
    });
  }

  // Les écrans d'authentification précèdent l'interface réservée aux utilisateurs connectés.
  if (!user) return <LoginScreen username={loginName} password={loginPassword} setUsername={setLoginName} setPassword={setLoginPassword} onSubmit={signIn} busy={busy} error={error} />;
  if (user.must_change_password) return <PasswordScreen user={user} currentPassword={currentPassword} newPassword={newPassword} setCurrentPassword={setCurrentPassword} setNewPassword={setNewPassword} onSubmit={changePassword} busy={busy} error={error} />;

  // Interface connectée : menu latéral, barre d'outils, module actif et fenêtres modales.
  return (
    <div className="app-shell">
      {mobileMenu && <button className="mobile-backdrop" aria-label="Fermer le menu" onClick={() => setMobileMenu(false)} />}
      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <div className="brand"><div className="brand-mark"><Church size={20} /></div><div><div className="brand-name">life<span>epm</span></div><div className="brand-caption">ÉGLISE PENTECÔTE MISSIONNAIRE</div></div><button className="icon-button mobile-close" onClick={() => setMobileMenu(false)} aria-label="Fermer"><X size={18} /></button></div>
        <div className="church-selector"><div className="church-emblem">{church?.logo_url ? <img className="church-logo-image" src={church.logo_url} alt={`Logo ${church.name}`} /> : <Church size={17} />}</div><div className="church-copy"><strong>{church?.name ?? "Église Pentecôte Missionnaire"}</strong><span>{church?.city ?? "Côte d'Ivoire"}</span></div><ChevronDown size={15} /></div>
        <nav className="main-nav" aria-label="Navigation principale">{visibleNavigationGroups.map((group) => <div className="nav-group" key={group.label}>
          <div className="nav-label">{group.label}</div>
          {group.items.map(({ id, label, icon: Icon }) => <button key={id} onClick={() => void selectSection(id)} className={`nav-item ${section === id ? "active" : ""}`}><Icon size={18} /><span>{label}</span></button>)}
        </div>)}</nav>
        <div className="sidebar-bottom"><div className="verse-card"><div className="verse-icon"><ShieldCheck size={16} /></div><p>« {bibleVerse.text} »</p><span>{bibleVerse.reference.toUpperCase()} · LSG 1910</span></div><button className="nav-item help-link" onClick={() => setNotice("Contactez votre administrateur pour obtenir de l'aide.")}><CircleHelp size={17} />Centre d'aide</button><div className="profile-card"><span className="avatar navy">{initials(user.full_name)}</span><div className="profile-copy"><strong>{user.full_name}</strong><span>{roleLabel(user.role)}</span></div><button className="icon-button" aria-label="Se déconnecter" onClick={() => void signOut()}><LogOut size={17} /></button></div></div>
      </aside>
      <main className="main-area">
        <header className="topbar"><div className="topbar-left"><button className="icon-button mobile-menu-button" onClick={() => setMobileMenu(true)} aria-label="Menu"><Menu size={20} /></button><div className="breadcrumb"><span>Life EPM</span><span>/</span><strong>{labels[section]}</strong></div></div><div className="topbar-actions"><label className="search-box"><Search size={16} /><input placeholder="Rechercher un fidèle" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runAction(() => loadSection("fideles", search)); }} /></label><span className="topbar-divider" /><span className="role-chip">{roleLabel(user.role)}</span><div className="topbar-profile"><span className="avatar">{initials(user.full_name)}</span><span className="topbar-profile-copy"><strong>{user.full_name}</strong><span>{roleLabel(user.role)}</span></span></div></div></header>
        <div className="page-content">
          {error && <div className="alert error-alert" role="alert">{error}<button onClick={() => setError("")} aria-label="Fermer"><X size={15} /></button></div>}
          {notice && <div className="alert success-alert" role="status"><Check size={15} />{notice}<button onClick={() => setNotice("")} aria-label="Fermer"><X size={15} /></button></div>}
          {section === "dashboard"
            ? <Dashboard user={user} data={dashboard} onNavigate={(target) => void selectSection(target)} />
            : section === "sms"
              ? <MessengerWorkspace user={user} />
              : <ModulePage section={section} rows={records} summary={summary} user={user} church={church} storyFilter={storyFilter} setStoryFilter={setStoryFilter} onSaveChurch={saveChurchIdentity} onUploadLogo={(file) => void saveChurchLogo(file)} onRemoveLogo={() => void removeChurchLogo()} busy={busy} search={search} setSearch={setSearch} familyTab={familyTab} setFamilyTab={(tab) => { setFamilyTab(tab); writePageLocation("familles", "tab", tab); void runAction(async () => setRecords(await api<RecordRow[]>(`/families/${tab}`))); }} financialTab={financialTab} setFinancialTab={(tab) => { setFinancialTab(tab); writePageLocation("finances", "tab", tab); void runAction(async () => { const [data, metrics] = await Promise.all([api<RecordRow[]>(tab === "budgets" ? "/budgets" : "/finances"), api<SummaryData>(`/financial-summary?year=${new Date().getFullYear()}`)]); setRecords(data); setSummary(metrics); }); }} serviceGroup={serviceGroup} setServiceGroup={selectServiceGroup} settingsTab={settingsTab} setSettingsTab={selectSettingsTab} onNavigate={(target) => void selectSection(target)} onCreate={() => void runAction(openRecordModal)} onEdit={openMemberEditor} onAttendance={(row) => void openAttendance(row)} onAnswerPrayer={(id) => void runEndpoint(`/prayers/${id}/answer`, "Le sujet est exaucé et son témoignage est ajouté.", () => void runAction(() => loadSection("prieres")), setNotice, setError)} onReload={() => void runAction(() => loadSection(section, search))} onNotice={setNotice} onError={setError} />}
        </div>
      </main>
      {familyChoiceOpen && <FamilyTypeDialog onClose={() => setFamilyChoiceOpen(false)} onChoose={(type) => void chooseFamilyEntry(type)} />}
      {modal && <RecordModal section={section} familyTab={familyTab} financialTab={financialTab} serviceGroup={serviceGroup} members={formMembers} initialRecord={editingRecord} onClose={() => { setModal(false); setEditingRecord(null); }} onSubmit={saveRecord} busy={busy} />}
      {attendanceTarget && <AttendanceModal service={attendanceTarget} members={attendanceMembers} onClose={() => setAttendanceTarget(null)} onSubmit={saveAttendance} busy={busy} />}
    </div>
  );
}

// Petits utilitaires d'affichage partagés par le menu et le profil utilisateur.
function initials(name: string) { return name.split(/\s+/).slice(0, 2).map((part) => part[0] ?? "").join("").toUpperCase(); }
function roleLabel(role: Role) { return ({ super_admin: "Super administrateur", secretary: "Secrétariat", treasurer: "Trésorerie", shepherd: "Encadrant / Berger" })[role]; }

// Écrans de connexion et de changement obligatoire du mot de passe provisoire.
function LoginScreen({ username, password, setUsername, setPassword, onSubmit, busy, error }: { username: string; password: string; setUsername: (value: string) => void; setPassword: (value: string) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; busy: boolean; error: string }) {
  return <main className="auth-page"><section className="auth-card"><div className="brand auth-brand"><div className="brand-mark"><Church size={22} /></div><div><div className="brand-name">life<span>epm</span></div><div className="brand-caption">ÉGLISE PENTECÔTE MISSIONNAIRE</div></div></div><div className="auth-heading"><span className="eyebrow">BIENVENUE DANS VOTRE ESPACE</span><h1>Connectez-vous</h1><p>Gérez votre communauté en toute simplicité.</p></div>{error && <div className="alert error-alert" role="alert">{error}</div>}<form onSubmit={onSubmit} className="auth-form"><label className="form-field"><span>Identifiant</span><input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} /></label><label className="form-field"><span>Mot de passe</span><input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label><button className="button button-primary auth-submit" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}<ArrowRight size={16} /></button></form><div className="auth-secure"><ShieldCheck size={15} />Connexion sécurisée · Église Pentecôte Missionnaire</div></section><div className="auth-decoration"><div className="auth-visual-top"><div className="brand-mark"><Church size={21} /></div><div><strong>life<span>epm</span></strong><small>ÉGLISE PENTECÔTE MISSIONNAIRE</small></div></div><div className="auth-cross" aria-hidden="true">✝</div><div className="auth-decoration-copy"><span>UNE ÉGLISE, UNE FAMILLE</span><strong>Servir avec foi.<br />Grandir ensemble.</strong><p>La vie de votre communauté, organisée dans un espace unique.</p><div className="auth-features"><div><Users size={18} /><span><strong>Une communauté unie</strong><small>Suivez les fidèles et les familles.</small></span></div><div><CalendarDays size={18} /><span><strong>Une vie bien organisée</strong><small>Cultes, programmes et événements.</small></span></div><div><ShieldCheck size={18} /><span><strong>Un espace sécurisé</strong><small>Les informations selon votre rôle.</small></span></div></div></div><div className="auth-visual-footer">© 2026 Life EPM <span /> Côte d’Ivoire</div></div></main>;
}

function PasswordScreen({ user, currentPassword, newPassword, setCurrentPassword, setNewPassword, onSubmit, busy, error }: { user: User; currentPassword: string; newPassword: string; setCurrentPassword: (value: string) => void; setNewPassword: (value: string) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; busy: boolean; error: string }) {
  return <main className="auth-page"><section className="auth-card password-card"><div className="brand auth-brand"><div className="brand-mark"><ShieldCheck size={21} /></div><div><div className="brand-name">Sécurisez votre compte</div><div className="brand-caption">PREMIÈRE CONNEXION · {user.full_name.toUpperCase()}</div></div></div><div className="auth-heading"><h1>Choisissez un nouveau mot de passe</h1><p>Pour protéger votre compte, modifiez le mot de passe provisoire avant de continuer.</p></div>{error && <div className="alert error-alert" role="alert">{error}</div>}<form onSubmit={onSubmit} className="auth-form"><label className="form-field"><span>Mot de passe actuel</span><input type="password" autoComplete="current-password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label><label className="form-field"><span>Nouveau mot de passe · 12 caractères minimum</span><input type="password" autoComplete="new-password" minLength={12} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label><button className="button button-primary auth-submit" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer et continuer"}<ArrowRight size={16} /></button></form><div className="auth-secure"><ShieldCheck size={15} />Votre mot de passe est chiffré avant stockage.</div></section></main>;
}

// Espace de messagerie, conversations privées, groupes et état de livraison SMS.
function MessengerWorkspace({ user }: { user: User }) {
  const [recipients, setRecipients] = useState<MessagingRecipient[]>([]);
  const [smsRecipients, setSmsRecipients] = useState<SmsRecipient[]>([]);
  const [smsMemberIds, setSmsMemberIds] = useState<number[]>([]);
  const [smsMessage, setSmsMessage] = useState("");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"internal" | "sms">("internal");
  const [showCompose, setShowCompose] = useState(false);
  const [recipientIds, setRecipientIds] = useState<number[]>([]);
  const [groupTitle, setGroupTitle] = useState("");
  const [firstMessage, setFirstMessage] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [smsNotice, setSmsNotice] = useState("");

  const refreshConversations = useCallback(async () => {
    setConversations(await api<ConversationSummary[]>("/conversations"));
  }, []);

  useEffect(() => {
    let active = true;
    const requests: [Promise<MessagingRecipient[]>, Promise<ConversationSummary[]>, Promise<SmsRecipient[] | null>] = [
      api<MessagingRecipient[]>("/messaging/recipients"),
      api<ConversationSummary[]>("/conversations"),
      ["super_admin", "secretary"].includes(user.role)
        ? api<SmsRecipient[]>("/communications/sms/recipients")
        : Promise.resolve(null),
    ];
    Promise.all(requests).then(([availableRecipients, availableConversations, eligibleSmsRecipients]) => {
      if (!active) return;
      setRecipients(availableRecipients);
      setConversations(availableConversations);
      setSmsRecipients(eligibleSmsRecipients ?? []);
      setActiveConversationId(availableConversations[0]?.id ?? null);
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "La messagerie est indisponible.");
    });
    return () => { active = false; };
  }, [user.role]);

  useEffect(() => {
    if (activeConversationId === null) {
      setMessages([]);
      return;
    }
    let active = true;
    const loadMessages = async () => {
      try {
        const data = await api<ChatMessage[]>(`/conversations/${activeConversationId}/messages`);
        if (active) {
          setMessages(data);
          await refreshConversations();
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Impossible de charger cette conversation.");
      }
    };
    void loadMessages();
    const interval = window.setInterval(() => { void loadMessages(); }, 8000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [activeConversationId, refreshConversations]);

  async function startConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const created = await api<ConversationSummary>("/conversations", {
        method: "POST",
        body: JSON.stringify({
          recipient_user_ids: recipientIds,
          title: recipientIds.length > 1 ? groupTitle : null,
          message: firstMessage,
        }),
      });
      await refreshConversations();
      setActiveConversationId(created.id);
      setShowCompose(false);
      setRecipientIds([]);
      setGroupTitle("");
      setFirstMessage("");
      setActiveTab("internal");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "La conversation n'a pas pu être créée.");
    } finally {
      setBusy(false);
    }
  }

  async function sendReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (activeConversationId === null) return;
    setError("");
    setBusy(true);
    try {
      const sent = await api<ChatMessage>(`/conversations/${activeConversationId}/messages`, {
        method: "POST",
        body: JSON.stringify({ body: reply }),
      });
      setMessages((current) => [...current, sent]);
      setReply("");
      await refreshConversations();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Le message n'a pas pu être envoyé.");
    } finally {
      setBusy(false);
    }
  }

  async function sendSmsBroadcast(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSmsNotice("");
    setBusy(true);
    try {
      const result = await api<{ recipient_count: number }>("/communications/sms", {
        method: "POST",
        body: JSON.stringify({ member_ids: smsMemberIds, message: smsMessage }),
      });
      setSmsMemberIds([]);
      setSmsMessage("");
      setSmsNotice(`Envoi mis en file pour ${result.recipient_count} fidèle(s).`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "L’envoi SMS a échoué.");
    } finally {
      setBusy(false);
    }
  }

  const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId);
  const totalUnread = conversations.reduce((total, conversation) => total + conversation.unread_count, 0);

  return <>
    <PageHeading
      eyebrow="COMMUNICATION"
      title="Messagerie"
      description="Échangez en privé ou en groupe avec les personnes ayant un compte dans l’église."
      action={activeTab === "internal" && <button className="button button-primary" onClick={() => { setShowCompose((shown) => !shown); setError(""); }}><Plus size={16} />Nouveau message</button>}
    />
    <div className="finance-tabs messenger-tabs" role="tablist" aria-label="Moyen de communication">
      <button role="tab" aria-selected={activeTab === "internal"} className={`finance-tab ${activeTab === "internal" ? "active" : ""}`} onClick={() => setActiveTab("internal")}>Messagerie interne{totalUnread > 0 && <span className="unread-tab-badge">{totalUnread}</span>}</button>
      {["super_admin", "secretary"].includes(user.role) && <button role="tab" aria-selected={activeTab === "sms"} className={`finance-tab ${activeTab === "sms" ? "active" : ""}`} onClick={() => setActiveTab("sms")}>SMS aux fidèles</button>}
    </div>
    {error && <div className="alert error-alert" role="alert">{error}<button onClick={() => setError("")} aria-label="Fermer"><X size={15} /></button></div>}
    {smsNotice && <div className="alert success-alert" role="status"><Check size={15} />{smsNotice}<button onClick={() => setSmsNotice("")} aria-label="Fermer"><X size={15} /></button></div>}
    {activeTab === "sms"
      ? <section className="panel messenger-compose messenger-sms-workspace">
        <div className="panel-heading"><div><h3>Envoyer un SMS</h3><p>Seuls les fidèles ayant un numéro et ayant accepté les SMS apparaissent ici.</p></div></div>
        {smsRecipients.length === 0
          ? <div className="alert"><MessageCircle size={15} /> Aucun fidèle n’a encore un accord SMS enregistré et un numéro valide.</div>
          : <form onSubmit={sendSmsBroadcast}>
            <fieldset className="recipient-picker"><legend>Destinataires ({smsMemberIds.length} sélectionné{smsMemberIds.length === 1 ? "" : "s"})</legend>{smsRecipients.map((recipient) => <label key={recipient.id}><input type="checkbox" checked={smsMemberIds.includes(recipient.id)} onChange={(event) => setSmsMemberIds((current) => event.target.checked ? [...current, recipient.id] : current.filter((id) => id !== recipient.id))} /><span>{recipient.name}</span><small>{recipient.phone}</small></label>)}</fieldset>
            <label className="form-field messenger-message-field"><span>Message · {smsMessage.length}/1000 caractères</span><textarea required maxLength={1000} rows={4} value={smsMessage} onChange={(event) => setSmsMessage(event.target.value)} placeholder="Écrivez votre annonce…" /></label>
            <div className="messenger-form-actions"><button className="button button-primary" disabled={busy || smsMemberIds.length === 0 || !smsMessage.trim()}><Send size={14} />{busy ? "Mise en file…" : "Envoyer le SMS"}</button></div>
          </form>}
        <div className="alert messenger-sms-notice"><MessageCircle size={19} /><div><strong>Envoi SMS conditionné à la configuration</strong><span>Les identifiants Africa’s Talking doivent être ajoutés au fichier privé .env. Tant qu’ils ne sont pas configurés, l’API refuse l’envoi et aucun SMS ne part.</span></div></div>
      </section>
      : <>
        {showCompose && <section className="panel messenger-compose">
          <div className="panel-heading"><div><h3>Nouveau message</h3><p>Choisissez une personne ou plusieurs pour créer un groupe.</p></div><button className="icon-button" aria-label="Fermer le formulaire" onClick={() => setShowCompose(false)}><X size={17} /></button></div>
          {recipients.length === 0
            ? <EmptyState label="Aucun autre compte actif ne peut recevoir de message." />
            : <form onSubmit={startConversation}>
              <fieldset className="recipient-picker"><legend>Destinataires *</legend>{recipients.map((recipient) => <label key={recipient.id}><input type="checkbox" checked={recipientIds.includes(recipient.id)} onChange={(event) => setRecipientIds((current) => event.target.checked ? [...current, recipient.id] : current.filter((id) => id !== recipient.id))} /><span>{recipient.full_name}</span><small>{roleLabel(recipient.role)}</small></label>)}</fieldset>
              {recipientIds.length > 1 && <label className="form-field messenger-group-title"><span>Nom du groupe *</span><input required maxLength={120} value={groupTitle} onChange={(event) => setGroupTitle(event.target.value)} placeholder="Ex. Équipe d’organisation" /></label>}
              <label className="form-field messenger-message-field"><span>Votre message *</span><textarea required maxLength={4000} rows={3} value={firstMessage} onChange={(event) => setFirstMessage(event.target.value)} placeholder="Écrivez votre message…" /></label>
              <div className="messenger-form-actions"><button className="button button-primary" disabled={busy || recipientIds.length === 0}><Send size={14} />{busy ? "Envoi…" : "Envoyer"}</button></div>
            </form>}
        </section>}
        <div className="messenger-layout">
          <section className="panel messenger-inbox">
            <div className="messenger-panel-heading"><h3>Conversations</h3>{totalUnread > 0 && <span className="unread-total">{totalUnread} non lu{totalUnread > 1 ? "s" : ""}</span>}</div>
            {conversations.length === 0
              ? <EmptyState label="Vos conversations apparaîtront ici." />
              : <div className="conversation-list">{conversations.map((conversation) => <button key={conversation.id} className={`conversation-item ${activeConversationId === conversation.id ? "active" : ""}`} onClick={() => { setActiveConversationId(conversation.id); setShowCompose(false); }}>
                <span className="conversation-avatar"><MessageCircle size={16} /></span><span className="conversation-copy"><strong>{conversation.title}</strong><span>{conversation.last_sender ? `${conversation.last_sender} : ` : ""}{conversation.last_message || "Aucun message"}</span><small>{formatDate(text(conversation.updated_at))} · {formatTime(text(conversation.updated_at))}</small></span>{conversation.unread_count > 0 && <span className="conversation-unread">{conversation.unread_count}</span>}
              </button>)}</div>}
          </section>
          <section className="panel messenger-chat">
            {activeConversation
              ? <>
                <div className="chat-heading"><span className="conversation-avatar"><MessageCircle size={17} /></span><div><h3>{activeConversation.title}</h3><p>{activeConversation.is_group ? "Groupe · " : ""}{activeConversation.participants.join(", ")}</p></div></div>
                <div className="chat-messages" aria-live="polite">{messages.map((message) => <article key={message.id} className={`chat-message ${message.sender_id === user.id ? "own-message" : ""}`}><span className="chat-sender">{message.sender_id === user.id ? "Vous" : message.sender_name}</span><p>{message.body}</p><time>{formatDate(text(message.created_at))} · {formatTime(text(message.created_at))}</time></article>)}</div>
                <form className="chat-reply" onSubmit={sendReply}><textarea aria-label="Votre message" rows={2} maxLength={4000} required value={reply} onChange={(event) => setReply(event.target.value)} placeholder="Écrivez votre message…" /><button className="button button-primary" disabled={busy || !reply.trim()}><Send size={15} />Envoyer</button></form>
              </>
              : <EmptyState label="Sélectionnez une conversation ou commencez un nouveau message." />}
          </section>
        </div>
      </>}
  </>;
}

function Dashboard({ user, data, onNavigate }: { user: User; data: DashboardData; onNavigate: (section: Section) => void }) {
  const finances = data.finance_month;
  const financialYear = data.finance_year;
  const roleHeadings: Record<Role, { eyebrow: string; description: string; welcome: string; focus: string }> = {
    super_admin: { eyebrow: "GOUVERNANCE DE L'ÉGLISE", description: "Vue d'ensemble de la communauté et de ses activités.", welcome: "Pilotez votre église.", focus: "Vue globale de l'église" },
    secretary: { eyebrow: "ESPACE SECRÉTARIAT", description: "Retrouvez les dossiers et événements à suivre au secrétariat.", welcome: "Organisez la vie de l'église.", focus: "Suivi administratif" },
    treasurer: { eyebrow: "ESPACE TRÉSORERIE", description: "Suivez les opérations et les prévisions financières de l'église.", welcome: "Gérez les finances avec clarté.", focus: "Synthèse de trésorerie" },
    shepherd: { eyebrow: "ESPACE BERGER", description: "Accompagnez les membres et les activités de votre périmètre.", welcome: "Prenez soin de votre communauté.", focus: "Activité de votre périmètre" },
  };
  const heading = roleHeadings[user.role];
  const stats: { label: string; value: string; icon: LucideIcon; tint: string }[] = user.role === "treasurer"
    ? [
      { label: "Recettes du mois", value: `${Number(finances?.income ?? 0).toLocaleString("fr-FR")} XOF`, icon: Wallet, tint: "teal" },
      { label: "Dépenses du mois", value: `${Number(finances?.expenses ?? 0).toLocaleString("fr-FR")} XOF`, icon: Wallet, tint: "red" },
      { label: "Produits prévus", value: `${Number(financialYear?.planned_products ?? 0).toLocaleString("fr-FR")} XOF`, icon: FileText, tint: "blue" },
      { label: "Charges prévues", value: `${Number(financialYear?.planned_charges ?? 0).toLocaleString("fr-FR")} XOF`, icon: FileText, tint: "red" },
    ]
    : user.role === "shepherd"
      ? [
        { label: "Fidèles du périmètre", value: text(data.total_members ?? 0), icon: Users, tint: "blue" },
        { label: "Présences pointées", value: text(data.total_presence ?? 0), icon: Check, tint: "teal" },
        { label: "Absences signalées", value: text(data.total_absences ?? 0), icon: X, tint: "red" },
      ]
      : user.role === "secretary"
        ? [
          { label: "Fidèles enregistrés", value: text(data.total_members ?? 0), icon: Users, tint: "blue" },
          { label: "Nouveaux ce mois", value: text(data.new_members_this_month ?? 0), icon: Heart, tint: "red" },
          { label: "Mariages suivis", value: text(data.marriages_count ?? 0), icon: Church, tint: "teal" },
          { label: "Naissances enregistrées", value: text(data.births_count ?? 0), icon: Heart, tint: "blue" },
        ]
        : [
          { label: "Fidèles enregistrés", value: text(data.total_members ?? 0), icon: Users, tint: "blue" },
          { label: "Nouveaux ce mois", value: text(data.new_members_this_month ?? 0), icon: Heart, tint: "red" },
          { label: "Sujets de prière", value: text(data.open_prayer_requests ?? 0), icon: ShieldCheck, tint: "teal" },
          { label: "Cultes planifiés", value: text(data.total_services ?? 0), icon: CalendarDays, tint: "blue" },
        ];
  const quickLinks: { label: string; target: Section; icon: LucideIcon }[] = user.role === "treasurer"
    ? [{ label: "Opérations financières", target: "finances", icon: Wallet }, { label: "Budgets & prévisions", target: "finances", icon: FileText }]
    : user.role === "shepherd"
      ? [{ label: "Fidèles de mon périmètre", target: "fideles", icon: Users }, { label: "Prières & témoignages", target: "prieres", icon: ShieldCheck }]
      : user.role === "secretary"
        ? [{ label: "Annuaire des fidèles", target: "fideles", icon: Users }, { label: "Cultes & programmes", target: "cultes", icon: CalendarDays }, { label: "Mariages & naissances", target: "familles", icon: Church }]
        : [{ label: "Annuaire des fidèles", target: "fideles", icon: Users }, { label: "Cultes & programmes", target: "cultes", icon: CalendarDays }, { label: "Finances & budgets", target: "finances", icon: Wallet }, { label: "Paramètres de l'église", target: "parametres", icon: Settings }];
  const service = data.upcoming_service;
  const program = data.upcoming_program;
  return <><PageHeading eyebrow={heading.eyebrow} title={`Bienvenue, ${user.full_name}`} description={heading.description} />
    <section className="welcome-banner"><div className="welcome-copy"><span className="welcome-kicker">ÉGLISE PENTECÔTE MISSIONNAIRE · {roleLabel(user.role).toUpperCase()}</span><h2>{heading.welcome}<br /><span>Servir avec foi.</span></h2><p>Une communauté enracinée dans la foi, unie dans le service.</p><button className="banner-button" onClick={() => onNavigate(user.role === "treasurer" ? "finances" : "fideles")}>{user.role === "treasurer" ? "Ouvrir la trésorerie" : "Accéder aux fidèles"} <ArrowRight size={15} /></button></div><div className="banner-art" aria-hidden="true"><div className="art-sun" /><div className="art-cross"><span /><i /></div><div className="art-hill art-hill-back" /><div className="art-hill art-hill-front" /></div></section>
    <div className="section-title-row"><div><h2>{heading.focus}</h2><p>Indicateurs adaptés à votre niveau d'accès</p></div><span className="role-chip">{roleLabel(user.role)}</span></div>
    <section className="stats-grid">{stats.map(({ label, value, icon: Icon, tint }) => <article className="stat-card" key={label}><div className="stat-top"><span>{label}</span><span className={`stat-icon ${tint}`}><Icon size={17} /></span></div><div className="stat-value">{value}</div><div className="stat-foot"><span>Données actualisées</span></div></article>)}</section>
    {!!data.birthdays_today?.length && <section className="panel birthday-notice"><CalendarDays size={17} /><strong>Anniversaires aujourd'hui</strong><span>{data.birthdays_today.map((item) => item.name).join(" · ")}</span></section>}
    <div className="dashboard-grid"><ScheduleCard title="Prochain culte" item={service} empty="Aucun culte planifié." onClick={() => onNavigate("cultes")} /><ScheduleCard title="Prochain programme" item={program} empty="Aucun programme planifié." onClick={() => onNavigate("cultes")} />
    <section className="panel quick-actions"><div className="panel-heading"><div><h3>Accès rapide</h3><p>Raccourcis autorisés pour votre rôle</p></div></div>{quickLinks.map(({ label, target, icon: Icon }) => <button key={label} onClick={() => onNavigate(target)}><Icon size={17} /><span>{label}</span><ArrowRight size={14} /></button>)}</section></div>
    <footer className="page-footer"><span>Life EPM · Église Pentecôte Missionnaire</span><span><i className="online-dot" />Connecté à la base de données de l'église</span></footer>
  </>;
}

function ScheduleCard({ title, item, empty, onClick }: { title: string; item?: RecordRow | null; empty: string; onClick: () => void }) {
  return <section className="panel"><div className="panel-heading"><div><h3>{title}</h3><p>À venir dans la communauté</p></div><CalendarDays size={18} className="accent-icon" /></div>{item ? <div className="service-summary"><strong>{text(item.title)}</strong><span>{formatDate(text(item.starts_at))} · {formatTime(text(item.starts_at))}</span><span>{text(item.service_type)} · {text(item.location)}</span><small>Responsable : {text(item.speaker)}</small></div> : <EmptyState label={empty} />}<button className="text-button" onClick={onClick}>Voir cultes & programmes <ArrowRight size={14} /></button></section>;
}

// Aiguillage des modules : chaque branche affiche les listes, synthèses ou paramètres d'une rubrique.
function ModulePage({ section, rows, summary, user, church, storyFilter, setStoryFilter, onSaveChurch, onUploadLogo, onRemoveLogo, busy, search, setSearch, familyTab, setFamilyTab, financialTab, setFinancialTab, serviceGroup, setServiceGroup, settingsTab, setSettingsTab, onNavigate, onCreate, onEdit, onAttendance, onAnswerPrayer, onReload, onNotice, onError }: { section: Section; rows: RecordRow[]; summary: SummaryData | null; user: User; church: ChurchIdentity | null; storyFilter: StoryFilter; setStoryFilter: (filter: StoryFilter) => void; onSaveChurch: (event: FormEvent<HTMLFormElement>) => void; onUploadLogo: (file: File) => void; onRemoveLogo: () => void; busy: boolean; search: string; setSearch: (value: string) => void; familyTab: "marriages" | "births"; setFamilyTab: (tab: "marriages" | "births") => void; financialTab: FinancialTab; setFinancialTab: (tab: FinancialTab) => void; serviceGroup: ServiceGroup; setServiceGroup: (group: ServiceGroup) => void; settingsTab: SettingsTab; setSettingsTab: (tab: SettingsTab) => void; onNavigate: (section: Section) => void; onCreate: () => void; onEdit: (row: RecordRow) => void; onAttendance: (service: RecordRow) => void; onAnswerPrayer: (id: number) => void; onReload: () => void; onNotice: (message: string) => void; onError: (message: string) => void }) {
  const allowedCreate = section === "fideles" || section === "familles" || section === "utilisateurs" ? user.role === "super_admin" || (section === "fideles" || section === "familles") && user.role === "secretary" : section === "parametres" ? user.role === "super_admin" && settingsTab === "zones" : section === "finances" || section === "budgets" ? user.role === "super_admin" || user.role === "treasurer" : ["super_admin", "secretary", "shepherd"].includes(user.role) && ["cultes", "prieres"].includes(section);
  const createLabels: Partial<Record<Section, string>> = { fideles: "Nouveau fidèle", cultes: serviceGroup === "culte" ? "Planifier un culte" : "Planifier un programme", finances: financialTab === "budgets" ? "Ajouter un budget" : "Nouvelle opération", budgets: "Ajouter un budget", prieres: "Ajouter une prière ou un témoignage", familles: "Ajouter un événement familial", parametres: "Ajouter une zone", utilisateurs: "Créer un utilisateur" };
  const columns = rows.length ? Object.keys(rows[0]).filter((key) => !["id", "church_id", "created_at", "created_by_id", "member_id", "parent_one_id", "parent_two_id", "partner_one_id", "partner_two_id", "zone_id", "cell_id", "is_confidential", "service_group"].includes(key)) : [];
  const title = section === "familles" ? familyTab === "marriages" ? "Mariages & fiançailles" : "Naissances" : section === "parametres" ? "Paramètres" : labels[section];
  const familyStats = familyTab === "marriages"
    ? [
      { label: "Fiançailles suivies", value: rows.filter((row) => row.engagement_status === "en cours").length, icon: Heart, tint: "red" },
      { label: "Mariages civils", value: rows.filter((row) => row.civil_date).length, icon: Church, tint: "blue" },
      { label: "Bénédictions nuptiales", value: rows.filter((row) => row.blessing_date).length, icon: Check, tint: "teal" },
      { label: "Dossiers de mariage", value: rows.length, icon: FileText, tint: "blue" },
    ]
    : [
      { label: "Naissances enregistrées", value: rows.length, icon: Heart, tint: "red" },
      { label: "Nées cette année", value: rows.filter((row) => String(row.birth_date).startsWith(String(new Date().getFullYear()))).length, icon: CalendarDays, tint: "blue" },
      { label: "Filles", value: rows.filter((row) => row.gender === "Femme").length, icon: Users, tint: "teal" },
      { label: "Garçons", value: rows.filter((row) => row.gender === "Homme").length, icon: Users, tint: "blue" },
    ];
  return <><PageHeading eyebrow={section === "parametres" ? "CONFIGURATION" : section === "finances" || section === "budgets" ? "GESTION FINANCIÈRE" : section === "cultes" ? "RASSEMBLEMENTS & COMMUNAUTÉ" : "ESPACE ÉGLISE"} title={title} description={moduleDescription(section)} action={allowedCreate && <button className="button button-primary" onClick={onCreate}><Plus size={16} />{createLabels[section]}</button>} />
    {section === "cultes" && <div className="finance-tabs service-tabs" role="tablist" aria-label="Type de rassemblement"><button role="tab" aria-selected={serviceGroup === "culte"} className={`finance-tab ${serviceGroup === "culte" ? "active" : ""}`} onClick={() => setServiceGroup("culte")}>Cultes</button><button role="tab" aria-selected={serviceGroup === "programme"} className={`finance-tab ${serviceGroup === "programme" ? "active" : ""}`} onClick={() => setServiceGroup("programme")}>Programmes</button></div>}
    {section === "familles" && <div className="finance-tabs"><button className={`finance-tab ${familyTab === "marriages" ? "active" : ""}`} onClick={() => setFamilyTab("marriages")}>Mariages & fiançailles</button><button className={`finance-tab ${familyTab === "births" ? "active" : ""}`} onClick={() => setFamilyTab("births")}>Naissances</button></div>}
    {section === "finances" && <div className="finance-tabs"><button className={`finance-tab ${financialTab === "operations" ? "active" : ""}`} onClick={() => setFinancialTab("operations")}>Opérations</button><button className={`finance-tab ${financialTab === "budgets" ? "active" : ""}`} onClick={() => setFinancialTab("budgets")}>Budgets & prévisions</button></div>}
    {section === "parametres" && <SettingsWorkspace tab={settingsTab} setTab={setSettingsTab} rows={rows} church={church} onSaveChurch={onSaveChurch} onUploadLogo={onUploadLogo} onRemoveLogo={onRemoveLogo} busy={busy} onCreate={onCreate} onNavigate={onNavigate} />}
    {section === "fideles" && rows.some((row) => row.is_demo) && <div className="demo-notice"><ShieldCheck size={16} /><span><strong>Fiches d’exemple</strong> Les personnes marquées « Démonstration » sont fictives et servent à découvrir l’annuaire.</span></div>}
    {section === "fideles" && summary && <SummaryCards title="Activité des fidèles" description="Présences et absences explicitement pointées, ainsi que les étapes spirituelles." items={[
      { label: "Fidèles suivis", value: summary.total_members ?? 0, icon: Users, tint: "blue" },
      { label: "Présences pointées", value: summary.total_presence ?? 0, icon: Check, tint: "teal" },
      { label: "Absences signalées", value: summary.total_absences ?? 0, icon: X, tint: "red" },
      { label: "Baptêmes d’eau", value: summary.water_baptisms ?? 0, icon: Heart, tint: "blue" },
      { label: "Baptêmes du Saint-Esprit", value: summary.spirit_baptisms ?? 0, icon: ShieldCheck, tint: "teal" },
    ]} />}
    {section === "cultes" && summary && <SummaryCards title={serviceGroup === "culte" ? "Tableau de bord des cultes" : "Tableau de bord des programmes"} description={`Taux calculé uniquement sur les pointages enregistrés (${summary.recorded_attendance ?? 0} au total).`} items={[
      { label: serviceGroup === "culte" ? "Cultes planifiés" : "Programmes planifiés", value: summary.total_services ?? 0, icon: CalendarDays, tint: "blue" },
      { label: "Présences", value: summary.total_presence ?? 0, icon: Check, tint: "teal" },
      { label: "Absences", value: summary.total_absences ?? 0, icon: X, tint: "red" },
      { label: "Taux de présence pointé", value: `${summary.attendance_rate ?? 0}%`, icon: Heart, tint: "blue" },
    ]} />}
    {section === "familles" && <SummaryCards title={familyTab === "marriages" ? "Suivi des mariages" : "Suivi des naissances"} description={familyTab === "marriages" ? "Étapes civiles et spirituelles des couples accompagnés." : "Naissances recensées dans les familles de l’église."} items={familyStats} />}
    {section === "finances" && summary && <SummaryCards title={`Pilotage financier · ${summary.year}`} description="Budgets prévisionnels et opérations comptabilisées en XOF sur l’exercice." items={[
      { label: "Produits prévus", value: formatXof(summary.planned_product), icon: FileText, tint: "blue" },
      { label: "Recettes réalisées", value: formatXof(summary.actual_income), icon: Wallet, tint: "teal" },
      { label: "Charges prévues", value: formatXof(summary.planned_charge), icon: FileText, tint: "blue" },
      { label: "Dépenses réalisées", value: formatXof(summary.actual_expenses), icon: Wallet, tint: "red" },
    ]} />}
    {section === "prieres" ? <StoryBoard rows={rows} filter={storyFilter} setFilter={setStoryFilter} canAnswer={user.role === "super_admin" || user.role === "shepherd"} onAnswer={onAnswerPrayer} /> : section !== "parametres" && <section className="panel table-panel">    <div className="table-heading"><div><h3>{section === "fideles" ? "Annuaire des fidèles" : title}</h3><p>{rows.length} enregistrement{rows.length === 1 ? "" : "s"} · données enregistrées dans la base de l'église</p></div><div className="table-tools">{section === "fideles" && <label className="table-search"><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") onReload(); }} placeholder="Rechercher..." /></label>}<button className="button button-outline button-compact" onClick={onReload}>Actualiser</button><button className="button button-outline button-compact" disabled={!rows.length} onClick={() => exportRowsCsv(rows, columns, title)}><Download size={14} />Exporter CSV</button></div></div>
      {rows.length ? <div className="table-scroll"><table><thead><tr>{columns.map((column) => <th key={column}>{columnLabel(column)}</th>)}{(section === "utilisateurs" || section === "cultes" && ["super_admin", "shepherd"].includes(user.role) || section === "fideles" && ["super_admin", "secretary"].includes(user.role)) && <th>ACTION</th>}</tr></thead><tbody>{rows.map((row) => <tr key={String(row.id)}>{columns.map((column) => <td key={column}>{column === "amount" || column === "planned_amount" ? `${Number(row[column]).toLocaleString("fr-FR")} ${text(row.currency ?? "XOF")}` : column === "is_demo" ? row.is_demo ? "Démo" : "Non" : column.endsWith("_date") || ["starts_at", "occurred_on", "arrival_date", "acquired_on", "birth_date", "engagement_date", "dowry_date", "civil_date", "blessing_date", "followed_up_on"].includes(column) ? formatDate(text(row[column])) : text(row[column])}</td>)}{section === "utilisateurs" && row.is_active && <td><button className="button button-outline button-compact" onClick={() => void runEndpoint(`/users/${row.id}/block`, "Compte bloqué.", onReload, onNotice, onError)}>Bloquer</button></td>}{section === "cultes" && ["super_admin", "shepherd"].includes(user.role) && <td><button className="button button-outline button-compact" onClick={() => onAttendance(row)}>Pointer un fidèle</button></td>}{section === "fideles" && ["super_admin", "secretary"].includes(user.role) && <td><button className="button button-outline button-compact" onClick={() => onEdit(row)}>Modifier</button></td>}</tr>)}</tbody></table></div> : section !== "sms" && <EmptyState label="Aucune donnée enregistrée pour le moment." />}
      <div className="table-pagination"><span>La liste est synchronisée avec l'API Life EPM.</span>{section === "finances" && <span className="privacy-badge"><ShieldCheck size={13} />Accès restreint · Trésorerie</span>}</div>
    </section>}
    {section === "utilisateurs" && user.role === "super_admin" && <section className="panel settings-help"><ShieldCheck size={18} /><div><strong>Comptes et rôles</strong><span>Les mots de passe initiaux sont définis par l'administrateur et doivent être changés à la première connexion.</span></div></section>}
    {section === "finances" && <div className="privacy-note"><ShieldCheck size={17} /><span><strong>Journal de trésorerie protégé.</strong> Les opérations ne peuvent pas être supprimées depuis cette interface.</span></div>}
  </>;
}

// Formatage des montants et cartes de synthèse réutilisables.
function formatXof(value: unknown) {
  return `${Number(value ?? 0).toLocaleString("fr-FR")} XOF`;
}

function SummaryCards({ title, description, items }: { title: string; description: string; items: { label: string; value: string | number; icon: LucideIcon; tint: string }[] }) {
  return <section className="summary-section">
    <div className="section-title-row"><div><h2>{title}</h2><p>{description}</p></div></div>
    <div className="stats-grid">{items.map(({ label, value, icon: Icon, tint }) => <article className="stat-card" key={label}>
      <div className="stat-top"><span>{label}</span><span className={`stat-icon ${tint}`}><Icon size={17} /></span></div>
      <div className={`stat-value ${String(value).length > 15 ? "stat-value-compact" : ""}`}>{value}</div>
      <div className="stat-foot"><span>Données enregistrées</span></div>
    </article>)}</div>
  </section>;
}

// Fenêtres de choix et cartes utilisées par les rubriques de l'église.
function FamilyTypeDialog({ onClose, onChoose }: { onClose: () => void; onChoose: (type: "marriages" | "births") => void }) {
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal-card family-type-dialog" role="dialog" aria-modal="true" aria-labelledby="family-type-heading">
      <div className="modal-header"><div><span className="eyebrow">DOSSIERS FAMILIAUX</span><h2 id="family-type-heading">Que souhaitez-vous enregistrer ?</h2><p>Choisissez le type d'événement pour ouvrir son formulaire dédié.</p></div><button className="icon-button" onClick={onClose} aria-label="Fermer"><X size={18} /></button></div>
      <div className="family-entry-choices">
        <button type="button" className="family-entry-choice" onClick={() => onChoose("marriages")}><span className="family-entry-icon"><Church size={20} /></span><strong>Un mariage</strong><span>Fiançailles, dot, mariage civil et bénédiction nuptiale.</span><ArrowRight size={16} /></button>
        <button type="button" className="family-entry-choice" onClick={() => onChoose("births")}><span className="family-entry-icon birth"><Heart size={20} /></span><strong>Une naissance</strong><span>Identité de l'enfant, date de naissance et parents.</span><ArrowRight size={16} /></button>
      </div>
    </section>
  </div>;
}

function StoryBoard({ rows, filter, setFilter, canAnswer, onAnswer }: { rows: RecordRow[]; filter: StoryFilter; setFilter: (filter: StoryFilter) => void; canAnswer: boolean; onAnswer: (id: number) => void }) {
  const filters: { id: StoryFilter; label: string }[] = [
    { id: "all", label: "Tout" },
    { id: "prayer", label: "Sujets de prière" },
    { id: "testimony", label: "Témoignages" },
  ];
  const visibleRows = filter === "all" ? rows : rows.filter((row) => row.record_kind === filter);
  return <section className="panel story-board">
    <div className="story-board-heading"><div><h3>Prières & témoignages</h3><p>Suivez les demandes, leur exaucement et les témoignages au même endroit.</p></div><div className="finance-tabs story-filters">{filters.map((item) => <button key={item.id} className={`finance-tab ${filter === item.id ? "active" : ""}`} onClick={() => setFilter(item.id)}>{item.label}</button>)}</div></div>
    {visibleRows.length ? <div className="story-list">{visibleRows.map((row) => {
      const isPrayer = row.record_kind === "prayer";
      return <article className="story-card" key={`${String(row.record_kind)}-${String(row.id)}`}>
        <div className="story-card-top"><span className={`story-type ${isPrayer ? "prayer" : "testimony"}`}>{isPrayer ? "Sujet de prière" : "Témoignage"}</span><span className="story-date">{formatDate(text(row.created_at))}</span></div>
        <h4>{text(isPrayer ? row.category : row.title)}</h4>
        <p className="story-author">{text(row.author_name ?? row.member_name)}</p>
        <p className="story-content">{text(row.content)}</p>
        <div className="story-card-bottom">{isPrayer ? <span className={`story-status ${row.is_answered ? "answered" : ""}`}>{row.is_answered ? "Exaucé · témoignage créé" : "En attente de prière"}</span> : <span className="story-status answered">Témoignage partagé</span>}
          {isPrayer && !row.is_answered && canAnswer && <button className="button button-outline button-compact" onClick={() => onAnswer(Number(row.id))}>Marquer comme exaucé</button>}
        </div>
      </article>;
    })}</div> : <EmptyState label={filter === "prayer" ? "Aucun sujet de prière enregistré." : filter === "testimony" ? "Aucun témoignage enregistré." : "Aucune prière ou aucun témoignage pour le moment."} />}
  </section>;
}

async function runEndpoint(path: string, message: string, reload: () => void, notify: (message: string) => void, reportError: (message: string) => void) {
  try { await api(path, { method: "POST" }); notify(message); reload(); }
  catch (error) { reportError(error instanceof Error ? error.message : "Une erreur est survenue."); }
}

// Construit les formulaires à partir de définitions par module ; ajouter les champs dans ces définitions.
function RecordModal({ section, familyTab, financialTab, serviceGroup, members, initialRecord, onClose, onSubmit, busy }: { section: Section; familyTab: "marriages" | "births"; financialTab: FinancialTab; serviceGroup: ServiceGroup; members: AttendanceMember[]; initialRecord: RecordRow | null; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; busy: boolean }) {
  const [storyKind, setStoryKind] = useState<"prayer" | "testimony">("prayer");
  const [familyEntryType, setFamilyEntryType] = useState<"choose" | "marriages" | "births">("choose");
  const fields: Partial<Record<Section, { name: string; label: string; type?: string; required?: boolean; options?: string[] }[]>> = {
    fideles: [
      { name: "first_name", label: "Prénom", required: true }, { name: "last_name", label: "Nom", required: true },
      { name: "phone", label: "Téléphone" }, { name: "email", label: "E-mail", type: "email" },
      { name: "sms_opt_in", label: "Autorise les SMS", options: ["false", "true"] },
      { name: "arrival_date", label: "Date d'arrivée", type: "date", required: true },
      { name: "birth_date", label: "Date de naissance", type: "date" },
      { name: "family_name", label: "Nom de famille" }, { name: "profession", label: "Profession" },
      { name: "languages", label: "Langues parlées" },
      { name: "spiritual_status", label: "Statut spirituel", options: ["néophyte", "membre simple", "ouvrier", "pasteur"] },
      { name: "gender", label: "Civilité", options: ["", "Femme", "Homme"] },
    ],
    cultes: [{ name: "title", label: serviceGroup === "culte" ? "Nom du culte" : "Nom du programme", required: true }, { name: "service_type", label: serviceGroup === "culte" ? "Nature du culte" : "Type de programme", required: true, options: serviceGroup === "culte" ? ["Culte dominical", "Culte de prière", "Veillée de prière", "Culte spécial", "Autre culte"] : ["Évangélisation", "Rencontre de jeunesse", "Rencontre des familles missionnaires", "Conférence", "Séminaire", "Retraite spirituelle", "Autre programme"] }, { name: "starts_at", label: "Date et heure", type: "datetime-local", required: true }, { name: "ends_at", label: "Fin", type: "datetime-local" }, { name: "speaker", label: "Orateur / responsable", required: false }, { name: "theme", label: "Thème" }, { name: "location", label: "Lieu" }],
    finances: financialTab === "operations"
      ? [{ name: "journal", label: "Journal", required: true, options: ["offrande", "dime", "voeu", "soutien", "divers", "tresorerie"] }, { name: "direction", label: "Type d'opération", required: true, options: ["recette", "depense", "transfert"] }, { name: "amount", label: "Montant (XOF)", type: "number", required: true }, { name: "description", label: "Description", required: true }, { name: "treasury_account", label: "Compte de départ ou de réception", options: ["caisse", "banque"] }, { name: "counterparty_account", label: "Autre compte (transfert)", options: ["", "caisse", "banque"] }, { name: "occurred_on", label: "Date", type: "date", required: true }]
      : [{ name: "fiscal_year", label: "Exercice", type: "number", required: true }, { name: "label", label: "Poste budgétaire", required: true }, { name: "budget_class", label: "Classe", required: true, options: ["charge", "produit"] }, { name: "planned_amount", label: "Montant prévu (XOF)", type: "number", required: true }],
    budgets: [{ name: "fiscal_year", label: "Exercice", type: "number", required: true }, { name: "label", label: "Poste budgétaire", required: true }, { name: "budget_class", label: "Classe", required: true, options: ["charge", "produit"] }, { name: "planned_amount", label: "Montant prévu (XOF)", type: "number", required: true }],
    familles: familyTab === "marriages"
      ? [{ name: "partner_one_id", label: "Premier partenaire", type: "member", required: true }, { name: "partner_two_id", label: "Second partenaire", type: "member", required: true }, { name: "engagement_date", label: "Date des fiançailles", type: "date" }, { name: "engagement_status", label: "Statut du couple", options: ["en cours", "rompues", "mariés"] }, { name: "breakup_reason", label: "Motif de rupture" }, { name: "dowry_date", label: "Date de la dot", type: "date" }, { name: "civil_date", label: "Date du mariage civil", type: "date" }, { name: "blessing_date", label: "Date de la bénédiction nuptiale", type: "date" }]
      : [{ name: "parent_one_id", label: "Parent 1 (facultatif)", type: "member" }, { name: "parent_two_id", label: "Parent 2 (facultatif)", type: "member" }, { name: "child_first_name", label: "Prénom de l'enfant", required: true }, { name: "child_last_name", label: "Nom de l'enfant", required: true }, { name: "birth_date", label: "Date de naissance", type: "date", required: true }, { name: "gender", label: "Sexe de l'enfant", options: ["", "Femme", "Homme"] }],
    utilisateurs: [{ name: "full_name", label: "Nom complet", required: true }, { name: "username", label: "Identifiant", required: true }, { name: "password", label: "Mot de passe provisoire (12 caractères min.)", type: "password", required: true }, { name: "role", label: "Rôle", required: true, options: ["secretary", "treasurer", "shepherd"] }],
    parametres: [{ name: "name", label: "Nom de la zone", required: true }],
  };
  const storyFields: { name: string; label: string; type?: string; required?: boolean; options?: string[] }[] = storyKind === "prayer"
    ? [
      { name: "member_id", label: "Fidèle concerné (facultatif)", type: "member" },
      { name: "category", label: "Catégorie de prière", required: true, options: ["guérison", "emploi", "fécondité", "mariage", "délivrance", "harmonie conjugale", "famille", "autre"] },
      { name: "author_name", label: "Nom de la personne (facultatif)" },
      { name: "content", label: "Sujet de prière", type: "textarea", required: true },
      { name: "is_confidential", label: "Confidentialité", options: ["true", "false"] },
    ]
    : [
      { name: "member_id", label: "Fidèle concerné (facultatif)", type: "member" },
      { name: "title", label: "Titre du témoignage", required: true },
      { name: "content", label: "Récit du témoignage", type: "textarea", required: true },
    ];
  const sectionFields = section === "prieres" ? storyFields : fields[section];
  if (!sectionFields) return null;
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="modal-heading">
      <div className="modal-header"><div><span className="eyebrow">ÉGLISE PENTECÔTE MISSIONNAIRE</span><h2 id="modal-heading">{initialRecord ? "Modifier la fiche du fidèle" : section === "prieres" ? storyKind === "prayer" ? "Nouveau sujet de prière" : "Nouveau témoignage" : section === "familles" ? familyTab === "marriages" ? "Nouveau dossier de mariage" : "Enregistrer une naissance" : section === "cultes" ? serviceGroup === "culte" ? "Planifier un culte" : "Planifier un programme" : labels[section]}</h2><p>{initialRecord ? "Corrigez les informations et l’accord de communication de ce fidèle." : section === "familles" ? familyTab === "marriages" ? "Suivez les fiançailles, la dot, le mariage civil et la bénédiction nuptiale." : "Enregistrez l'enfant et rattachez ses parents, s'ils sont membres." : section === "cultes" ? serviceGroup === "culte" ? "Préparez les informations du culte et de son orateur." : "Planifiez une activité d'évangélisation, de jeunesse, de familles missionnaires ou autre." : "Les informations sont enregistrées dans la base de données."}</p></div><button className="icon-button" onClick={onClose} aria-label="Fermer"><X size={18} /></button></div>
      <form onSubmit={onSubmit}>
        {section === "cultes" && <input type="hidden" name="service_group" value={serviceGroup} />}
        {section === "prieres" && <label className="form-field story-kind-field"><span>Qu'ajoutez-vous ?</span><select name="record_kind" value={storyKind} onChange={(event) => setStoryKind(event.target.value as "prayer" | "testimony")}><option value="prayer">Sujet de prière</option><option value="testimony">Témoignage</option></select></label>}
        <div className="form-grid">{sectionFields.map((field) => {
          const initialValue = initialRecord?.[field.name];
          const initialText = initialValue === null || initialValue === undefined ? "" : String(initialValue);
          const defaultValue = initialRecord
            ? initialText
            : field.name === "is_confidential"
              ? "true"
              : field.name === "sms_opt_in"
                ? "false"
              : field.options?.[0] ?? "";
          return <label key={field.name} className={`form-field ${field.type === "textarea" ? "full-field" : ""}`}><span>{field.label}{field.required && <i> *</i>}</span>{field.type === "member" ? <select name={field.name} required={field.required} defaultValue={initialText}><option value="">{field.required ? "Choisir un fidèle" : "Aucun fidèle associé"}</option>{members.map((member) => <option key={member.id} value={member.id}>{member.church_number} · {member.first_name} {member.last_name}</option>)}</select> : field.options ? <select name={field.name} required={field.required} defaultValue={defaultValue}>{field.options.map((option) => <option key={option} value={option}>{field.name === "is_confidential" ? option === "true" ? "Confidentiel" : "Visible à l'équipe" : field.name === "sms_opt_in" ? option === "true" ? "Oui, j’accepte" : "Non" : option || "Non renseigné"}</option>)}</select> : field.type === "textarea" ? <textarea name={field.name} rows={4} required={field.required} defaultValue={initialText} /> : <input name={field.name} type={field.type ?? "text"} required={field.required} defaultValue={field.type === "password" ? undefined : initialText} min={field.type === "number" && field.name.includes("amount") ? "0.01" : undefined} step={field.type === "number" && field.name.includes("amount") ? "0.01" : undefined} minLength={field.type === "password" ? 12 : undefined} />}</label>;
        })}</div>
        <div className="modal-note"><ShieldCheck size={15} />Accès et enregistrement protégés selon votre rôle.</div>
        <div className="modal-actions"><button type="button" className="button button-outline" onClick={onClose}>Annuler</button><button className="button button-primary" disabled={busy}><Check size={15} />{busy ? "Enregistrement…" : initialRecord ? "Enregistrer les modifications" : "Enregistrer"}</button></div>
      </form>
    </section>
  </div>;
}

// Formulaires d'identité de l'église et de pointage des présences.
function ChurchIdentityForm({ church, onSubmit, busy }: { church: ChurchIdentity | null; onSubmit: (event: FormEvent<HTMLFormElement>) => void; busy: boolean }) {
  return <section className="panel church-settings">
    <div className="church-settings-heading"><h3>Identité de l'église</h3><span>Ces informations apparaissent dans l'application et servent à générer les numéros de vie d'église.</span></div>
    <form className="form-grid church-identity-fields" onSubmit={onSubmit}>
      <label className="form-field"><span>Nom affiché</span><input name="name" required minLength={2} maxLength={180} defaultValue={church?.name ?? "Église Pentecôte Missionnaire"} /></label>
      <label className="form-field"><span>Dénomination</span><input name="denomination" required minLength={2} maxLength={180} defaultValue={church?.denomination ?? "Église Pentecôte Missionnaire"} /></label>
      <label className="form-field"><span>Initiales</span><input name="initials" required minLength={2} maxLength={12} defaultValue={church?.initials ?? "EPM"} /></label>
      <label className="form-field"><span>Ville</span><input name="city" required minLength={2} maxLength={100} defaultValue={church?.city ?? "Abidjan"} /></label>
      <div className="modal-actions full-field"><button className="button button-primary" disabled={busy}><Check size={15} />{busy ? "Enregistrement…" : "Enregistrer l'identité"}</button></div>
    </form>
  </section>;
}

function CertificateWorkspace({ church }: { church: ChurchIdentity | null }) {
  const [members, setMembers] = useState<RecordRow[]>([]);
  const [memberId, setMemberId] = useState("");
  const [kind, setKind] = useState<"membership" | "baptism">("membership");
  const [issuedOn, setIssuedOn] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  });
  const [officiant, setOfficiant] = useState("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let active = true;
    api<RecordRow[]>("/members?limit=200")
      .then((data) => { if (active) setMembers(data); })
      .catch((reason: unknown) => {
        if (active) setLoadError(reason instanceof Error ? reason.message : "Impossible de charger les fidèles.");
      });
    return () => { active = false; };
  }, []);

  const member = members.find((item) => String(item.id) === memberId);
  const name = member ? `${text(member.first_name)} ${text(member.last_name)}` : "";
  const hasBaptismDate = Boolean(member?.water_baptism_date);

  return <section className="panel certificate-workspace">
    <div className="panel-heading"><div><h3>Créer un certificat imprimable</h3><p>Choisissez un fidèle puis imprimez ou enregistrez le document en PDF depuis le navigateur.</p></div></div>
    {loadError && <div className="alert error-alert" role="alert">{loadError}</div>}
    <div className="certificate-form">
      <label className="form-field"><span>Type de document</span><select value={kind} onChange={(event) => setKind(event.target.value as "membership" | "baptism")}><option value="membership">Attestation de membre</option><option value="baptism" disabled={!hasBaptismDate}>Certificat de baptême d'eau{member && !hasBaptismDate ? " · date à renseigner dans la fiche" : ""}</option></select></label>
      <label className="form-field"><span>Fidèle</span><select required value={memberId} onChange={(event) => setMemberId(event.target.value)}><option value="">Choisir un fidèle</option>{members.map((item) => <option key={String(item.id)} value={String(item.id)}>{text(item.church_number)} · {text(item.first_name)} {text(item.last_name)}</option>)}</select></label>
      <label className="form-field"><span>Date d'émission</span><input type="date" required value={issuedOn} onChange={(event) => setIssuedOn(event.target.value)} /></label>
      <label className="form-field"><span>Nom du signataire</span><input maxLength={160} value={officiant} onChange={(event) => setOfficiant(event.target.value)} placeholder="Pasteur / responsable" /></label>
    </div>
    {member && <div className="certificate-print-surface">
      <article className="certificate-paper">
        <div className="certificate-frame">
          <div className="certificate-brand">{church?.logo_url && <img src={church.logo_url} alt="" />}<div><strong>{church?.name ?? "Église Pentecôte Missionnaire"}</strong><span>{church?.denomination ?? "Église Pentecôte Missionnaire"} · {church?.city ?? ""}</span></div></div>
          <div className="certificate-ornament" aria-hidden="true">✦</div>
          <p className="certificate-kicker">ATTESTATION OFFICIELLE</p>
          <h2>{kind === "membership" ? "Attestation de membre" : "Certificat de baptême d'eau"}</h2>
          <p className="certificate-intro">{kind === "membership" ? "Nous attestons que" : "Nous attestons que le baptême d'eau de"}</p>
          <strong className="certificate-member-name">{name}</strong>
          <p className="certificate-details">{kind === "membership"
            ? `N° ${text(member.church_number)} · membre depuis le ${formatDate(text(member.arrival_date))}.`
            : `N° ${text(member.church_number)} · baptisé(e) le ${formatDate(text(member.water_baptism_date))}.`}</p>
          <p className="certificate-body">{kind === "membership"
            ? "est reconnu(e) comme membre de notre communauté et participe à la vie de l'église."
            : "a été célébré conformément à la foi et à la pratique de notre communauté."}</p>
          <p className="certificate-issued">Fait à {church?.city ?? "________________"}, le {formatDate(issuedOn)}.</p>
          <div className="certificate-signature"><span className="certificate-signature-line" /><strong>{officiant || "Le responsable de l'église"}</strong><small>Signature et cachet</small></div>
        </div>
      </article>
    </div>}
    <div className="certificate-actions"><p>Le document est imprimé par votre navigateur et n'est pas archivé dans Life EPM.</p><button className="button button-primary" type="button" disabled={!member || kind === "baptism" && !hasBaptismDate} onClick={() => window.print()}><FileText size={15} />Imprimer / Enregistrer en PDF</button></div>
  </section>;
}

function SettingsWorkspace({ tab, setTab, rows, church, onSaveChurch, onUploadLogo, onRemoveLogo, busy, onCreate, onNavigate }: { tab: SettingsTab; setTab: (tab: SettingsTab) => void; rows: RecordRow[]; church: ChurchIdentity | null; onSaveChurch: (event: FormEvent<HTMLFormElement>) => void; onUploadLogo: (file: File) => void; onRemoveLogo: () => void; busy: boolean; onCreate: () => void; onNavigate: (section: Section) => void }) {
  const tabs: { id: SettingsTab; label: string; icon: LucideIcon }[] = [
    { id: "identity", label: "Identité de l'église", icon: Church },
    { id: "zones", label: "Zones & cellules", icon: MapPin },
    { id: "users", label: "Utilisateurs & rôles", icon: Users },
    { id: "certificates", label: "Certificats", icon: FileText },
  ];
  const title = tabs.find((item) => item.id === tab)?.label ?? "Paramètres";
  return <section className="settings-layout">
    <nav className="settings-nav" aria-label="Rubriques des paramètres">{tabs.map(({ id, label, icon: Icon }) => <button key={id} className={`settings-nav-item ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}><Icon size={17} /><span>{label}</span><ArrowRight size={14} /></button>)}</nav>
    <div className="settings-content">
      <div className="settings-content-heading"><div><h2>{title}</h2><p>{tab === "identity" ? "Informations générales affichées dans votre espace Life EPM." : tab === "zones" ? "Gérez vos zones, secteurs et cellules de prière." : tab === "users" ? "Les permissions doivent être configurées côté serveur avant toute mise en production." : "Préparez vos certificats de baptême et lettres de recommandation."}</p></div></div>
      {tab === "identity" && <div className="panel settings-identity-panel">
        <div className="settings-logo-row">
          <span className="church-emblem settings-logo-preview">{church?.logo_url ? <img className="church-logo-image" src={church.logo_url} alt={`Logo ${church.name}`} /> : <Church size={20} />}</span>
          <div><strong>Logo de l'église</strong><span>PNG, JPEG ou WebP · 2 Mo maximum</span></div>
          <label className={`button button-outline button-compact ${busy ? "logo-upload-disabled" : ""}`}>
            {church?.logo_url ? "Remplacer" : "Choisir un logo"}
            <input className="logo-file-input" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              event.currentTarget.value = "";
              if (file) onUploadLogo(file);
            }} />
          </label>
          {church?.logo_url && <button className="button button-outline button-compact" type="button" disabled={busy} onClick={onRemoveLogo}>Supprimer</button>}
        </div>
        <ChurchIdentityForm church={church} onSubmit={onSaveChurch} busy={busy} />
      </div>}
      {tab === "zones" && <div className="panel settings-feature-card"><div className="settings-feature-icon"><MapPin size={21} /></div><div className="settings-feature-copy"><strong>Organisation géographique</strong><span>Gérez vos zones, secteurs et cellules de prière.</span>{rows.length > 0 && <div className="settings-zone-list">{rows.map((row) => <span className="settings-zone-chip" key={String(row.id)}>{text(row.name)}</span>)}</div>}</div><button className="button button-outline" onClick={onCreate}><Plus size={14} />Ajouter une zone</button></div>}
      {tab === "users" && <div className="panel settings-feature-card"><div className="settings-feature-icon"><ShieldCheck size={21} /></div><div className="settings-feature-copy"><strong>Accès & permissions</strong><span>Consultez les comptes et gérez les rôles autorisés dans votre église.</span></div><button className="button button-outline" onClick={() => onNavigate("utilisateurs")}>Gérer les utilisateurs <ArrowRight size={14} /></button></div>}
      {tab === "certificates" && <CertificateWorkspace church={church} />}
    </div>
  </section>;
}

function AttendanceModal({ service, members, onClose, onSubmit, busy }: { service: RecordRow; members: AttendanceMember[]; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; busy: boolean }) {
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="attendance-heading">
    <div className="modal-header"><div><span className="eyebrow">CULTE & PRÉSENCES</span><h2 id="attendance-heading">Pointer un fidèle</h2><p>{text(service.title)}</p></div><button className="icon-button" onClick={onClose} aria-label="Fermer"><X size={18} /></button></div>
    {members.length ? <form onSubmit={onSubmit}><label className="form-field"><span>Fidèle</span><select name="member_id" required defaultValue=""><option value="" disabled>Choisir une personne</option>{members.map((member) => <option key={member.id} value={member.id}>{member.church_number} · {member.first_name} {member.last_name}</option>)}</select></label><label className="form-field attendance-status-field"><span>Statut du pointage</span><select name="present" defaultValue="true"><option value="true">Présent</option><option value="false">Absent</option></select></label><div className="modal-note"><ShieldCheck size={15} />Les absences ne sont comptées que lorsqu'elles sont signalées explicitement.</div><div className="modal-actions"><button type="button" className="button button-outline" onClick={onClose}>Annuler</button><button className="button button-primary" disabled={busy}><Check size={15} />{busy ? "Enregistrement…" : "Enregistrer le pointage"}</button></div></form> : <><EmptyState label="Aucun fidèle disponible pour le pointage." /><div className="modal-actions"><button type="button" className="button button-outline" onClick={onClose}>Fermer</button></div></>}
  </section></div>;
}

// En-têtes de page, états vides et libellés des champs renvoyés par l'API.
function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
function EmptyState({ label }: { label: string }) { return <div className="empty-state"><FileText size={23} /><span>{label}</span></div>; }
function moduleDescription(section: Section) {
  return ({ fideles: "Consultez l’activité, les pointages et les étapes spirituelles des membres.", cultes: "Planifiez les cultes et suivez les présences et absences signalées.", finances: "Pilotez les opérations de trésorerie et les budgets depuis un espace commun.", budgets: "Préparez et suivez les budgets de l'église.", prieres: "Enregistrez les sujets de prière, suivez leur réponse et partagez les témoignages au même endroit.", familles: "Accompagnez séparément les mariages, fiançailles et naissances.", parametres: "Gérez les zones géographiques de votre église.", utilisateurs: "Créez des comptes et attribuez les rôles d'accès.", sms: "Échangez en privé ou en groupe avec les comptes de votre église.", dashboard: "" })[section];
}
function columnLabel(key: string) {
  const known: Record<string, string> = { church_number: "NUMÉRO EPM", first_name: "PRÉNOM", last_name: "NOM", is_demo: "FICHE DÉMO", gender: "CIVILITÉ", address: "ADRESSE", marital_status: "SITUATION MATRIMONIALE", spiritual_status: "STATUT SPIRITUEL", arrival_date: "DATE D'ARRIVÉE", conversion_date: "CONVERSION", water_baptism_date: "BAPTÊME D'EAU", spirit_baptism_date: "BAPTÊME DU SAINT-ESPRIT", origin_church: "ÉGLISE D'ORIGINE", departure_status: "DÉPART", birth_date: "NAISSANCE", phone: "TÉLÉPHONE", email: "E-MAIL", family_name: "FAMILLE", profession: "PROFESSION", languages: "LANGUES", title: "INTITULÉ", service_type: "TYPE", starts_at: "DATE & HEURE", speaker: "ORATEUR", theme: "THÈME", location: "LIEU", attendance_count: "PRÉSENCES", category: "CATÉGORIE", content: "SUJET", is_answered: "EXAUCÉ", is_active: "COMPTE ACTIF", must_change_password: "CHANGEMENT DU MOT DE PASSE REQUIS", role: "RÔLE", username: "IDENTIFIANT", full_name: "NOM COMPLET", journal: "JOURNAL", direction: "TYPE", amount: "MONTANT", planned_amount: "MONTANT PRÉVU", budget_class: "CLASSE", class: "CLASSE", fiscal_year: "EXERCICE", currency: "DEVISE", description: "DESCRIPTION", treasury_account: "COMPTE", counterparty_account: "COMPTE DESTINATAIRE", occurred_on: "DATE", name: "NOM", condition: "ÉTAT", acquired_on: "ACQUISITION", denomination: "DÉNOMINATION", city: "VILLE", engagement_status: "STATUT DES FIANÇAILLES", breakup_reason: "MOTIF DE RUPTURE", child_first_name: "PRÉNOM DE L'ENFANT", child_last_name: "NOM DE L'ENFANT" };
  return known[key] ?? key.replaceAll("_", " ").toUpperCase();
}
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString("fr-FR"); }
function formatTime(value: string) { const date = new Date(value); return Number.isNaN(date.valueOf()) ? "" : date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }); }
