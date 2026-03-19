"""
Shared matplotlib helpers for embedding dark/light-themed figures.
Call apply_theme(dark) before any draw to switch palettes globally.
"""
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

# ── Palette definitions ───────────────────────────────────────────────────────

_DARK = dict(
    FIG_BG      = '#1e1e2e',
    AXES_BG     = '#181825',
    GRID_COLOR  = '#313244',
    SPINE_COLOR = '#313244',
    TICK_COLOR  = '#6c7086',
    TEXT_COLOR  = '#cdd6f4',
    LEGEND_BG   = '#252535',
    PLACEHOLDER = '#6c7086',
    AXIS_X      = '#89b4fa',
    AXIS_Y      = '#f38ba8',
    AXIS_Z      = '#a6e3a1',
    CURSOR_BG   = '#1e1e2e',
    CURSOR_TEXT = '#cdd6f4',
)

_LIGHT = dict(
    FIG_BG      = '#eff1f5',
    AXES_BG     = '#ffffff',
    GRID_COLOR  = '#ccd0da',
    SPINE_COLOR = '#bcc0cc',
    TICK_COLOR  = '#9ca0b0',
    TEXT_COLOR  = '#4c4f69',
    LEGEND_BG   = '#f0f2fa',
    PLACEHOLDER = '#9ca0b0',
    AXIS_X      = '#1e66f5',
    AXIS_Y      = '#d20f39',
    AXIS_Z      = '#40a02b',
    CURSOR_BG   = '#eff1f5',
    CURSOR_TEXT = '#4c4f69',
)

# ── Module-level colour globals (start dark) ──────────────────────────────────

_dark = False  # tracks current theme; read by tabs to style overlay buttons

FIG_BG      = _LIGHT['FIG_BG']
AXES_BG     = _LIGHT['AXES_BG']
GRID_COLOR  = _LIGHT['GRID_COLOR']
SPINE_COLOR = _LIGHT['SPINE_COLOR']
TICK_COLOR  = _LIGHT['TICK_COLOR']
TEXT_COLOR  = _LIGHT['TEXT_COLOR']
LEGEND_BG   = _LIGHT['LEGEND_BG']
PLACEHOLDER = _LIGHT['PLACEHOLDER']
CURSOR_BG   = _LIGHT['CURSOR_BG']
CURSOR_TEXT = _LIGHT['CURSOR_TEXT']

# Mutable dict — imported references stay valid after apply_theme
AXIS_COLORS = {
    'X': _LIGHT['AXIS_X'],
    'Y': _LIGHT['AXIS_Y'],
    'Z': _LIGHT['AXIS_Z'],
}


def apply_theme(dark: bool):
    """Update all module-level colour globals for the chosen theme."""
    global _dark, FIG_BG, AXES_BG, GRID_COLOR, SPINE_COLOR, TICK_COLOR, TEXT_COLOR
    global LEGEND_BG, PLACEHOLDER, CURSOR_BG, CURSOR_TEXT
    _dark = dark
    p = _DARK if dark else _LIGHT
    FIG_BG      = p['FIG_BG']
    AXES_BG     = p['AXES_BG']
    GRID_COLOR  = p['GRID_COLOR']
    SPINE_COLOR = p['SPINE_COLOR']
    TICK_COLOR  = p['TICK_COLOR']
    TEXT_COLOR  = p['TEXT_COLOR']
    LEGEND_BG   = p['LEGEND_BG']
    PLACEHOLDER = p['PLACEHOLDER']
    CURSOR_BG   = p['CURSOR_BG']
    CURSOR_TEXT = p['CURSOR_TEXT']
    AXIS_COLORS.update(X=p['AXIS_X'], Y=p['AXIS_Y'], Z=p['AXIS_Z'])


def make_canvas(parent=None) -> tuple[Figure, FigureCanvasQTAgg, NavigationToolbar2QT]:
    """Create a themed Figure + Canvas + Toolbar tuple."""
    fig = Figure(facecolor=FIG_BG, tight_layout=True)
    canvas = FigureCanvasQTAgg(fig)
    toolbar = NavigationToolbar2QT(canvas, parent)
    return fig, canvas, toolbar


def style_axes(ax, title='', xlabel='', ylabel='', title_color=None):
    """Apply current-theme styling to an Axes object."""
    if title_color is None:
        title_color = TEXT_COLOR
    ax.set_facecolor(AXES_BG)
    ax.set_title(title, color=title_color, fontsize=10, pad=4)
    ax.set_xlabel(xlabel, color=TICK_COLOR, fontsize=8)
    ax.set_ylabel(ylabel, color=TICK_COLOR, fontsize=8)
    ax.tick_params(colors=TICK_COLOR, labelsize=8)
    ax.grid(True, color=GRID_COLOR, alpha=0.8, linewidth=0.6)
    for spine in ax.spines.values():
        spine.set_edgecolor(SPINE_COLOR)


def placeholder_axes(fig, message='Load a .bin file to begin'):
    """Fill a figure with a single placeholder text axes."""
    fig.clear()
    fig.patch.set_facecolor(FIG_BG)
    ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor(AXES_BG)
    ax.text(0.5, 0.5, message,
            ha='center', va='center',
            color=PLACEHOLDER, fontsize=13,
            transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor(SPINE_COLOR)


def retheme_axes(ax, title_color=None):
    """
    Repaint an existing axes with the current theme colours without
    clearing or redrawing it (preserves zoom / pan / data).
    """
    ax.set_facecolor(AXES_BG)
    if title_color:
        ax.title.set_color(title_color)
    ax.xaxis.label.set_color(TICK_COLOR)
    ax.yaxis.label.set_color(TICK_COLOR)
    ax.tick_params(colors=TICK_COLOR, labelsize=8)
    ax.grid(True, color=GRID_COLOR, alpha=0.8, linewidth=0.6)
    for spine in ax.spines.values():
        spine.set_edgecolor(SPINE_COLOR)
    leg = ax.get_legend()
    if leg is not None:
        leg.get_frame().set_facecolor(LEGEND_BG)
        leg.get_frame().set_edgecolor(SPINE_COLOR)
        for text in leg.get_texts():
            text.set_color(TEXT_COLOR)


def add_legend(ax, *, ncol=1):
    ax.legend(
        fontsize=7,
        facecolor=LEGEND_BG,
        edgecolor=SPINE_COLOR,
        labelcolor=TEXT_COLOR,
        loc='upper right',
        ncol=ncol,
    )
