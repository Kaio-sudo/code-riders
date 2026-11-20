
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm";

const SUPABASE_URL = "https://dmopfcfqafczgytnziah.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_a5T_Eau1Jqswgj5DNV-PHg_jOnAqVRX";

export const supabase = createClient(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
);
