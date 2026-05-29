type ManagerLike = {
  entry_name?: string | number | null;
  player_name?: string | number | null;
};

const RESET_TEAM_NAMES = new Set(["restored", "change name", "deleted", "�"]);

export function isResetTeamName(name?: string | number | null) {
  return RESET_TEAM_NAMES.has(String(name ?? "").trim().toLowerCase());
}

export function primaryManagerName(row: ManagerLike) {
  const team = String(row.entry_name ?? "").trim();
  const player = String(row.player_name ?? "").trim();
  return isResetTeamName(team) ? player || "Name reset by FPL" : team || player || "Unknown manager";
}

export function secondaryManagerName(row: ManagerLike) {
  const team = String(row.entry_name ?? "").trim();
  const player = String(row.player_name ?? "").trim();
  if (isResetTeamName(team)) {
    return "Team name reset by FPL";
  }
  return player;
}

export function managerIdentity(row?: ManagerLike) {
  if (!row) {
    return "";
  }
  const primary = primaryManagerName(row);
  const secondary = secondaryManagerName(row);
  return secondary ? `${primary} - ${secondary}` : primary;
}
