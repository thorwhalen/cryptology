-- Pandoc filter: a blockquote that starts with **In the app:** is a pointer into the
-- cryptology app (https://apps.thorwhalen.com/cryptology/). In markdown it stays a plain
-- blockquote, so GitHub shows it well. In a PDF it becomes a light green box (the `appbox`
-- environment, defined in book/latex-header.tex); in HTML a <div class="in-app">.

local LEAD = "In the app:"

local function is_app_box(el)
  local first = el.content[1]
  if not first or (first.t ~= "Para" and first.t ~= "Plain") then return false end
  local strong = first.content[1]
  return strong and strong.t == "Strong" and pandoc.utils.stringify(strong) == LEAD
end

function BlockQuote(el)
  if not is_app_box(el) then return nil end
  if FORMAT:match("latex") then
    local out = { pandoc.RawBlock("latex", "\\begin{appbox}") }
    for _, b in ipairs(el.content) do table.insert(out, b) end
    table.insert(out, pandoc.RawBlock("latex", "\\end{appbox}"))
    return out
  elseif FORMAT:match("html") then
    return pandoc.Div(el.content, pandoc.Attr("", { "in-app" }, {}))
  end
  return nil
end
