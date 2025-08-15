# chess_cli_v3.py — mini échecs console avec :
# - roque, prise en passant
# - promotion au choix (q/r/b/n)
# - règle des 50 coups (auto nulle à 100 demi-coups)
# - nulle par triple répétition (auto)
# - sauvegarde/chargement (save/load)
from typing import List, Tuple, Optional, Iterable, Dict
import json
import os

Board = List[List[str]]
Square = Tuple[int, int]

def init_board() -> Board:
    return [
        list("rnbqkbnr"),
        list("pppppppp"),
        list("........"),
        list("........"),
        list("........"),
        list("........"),
        list("PPPPPPPP"),
        list("RNBQKNRB".replace("NRB","NBR"))  # safety no; we'll use correct row below
    ]

# Correct last row (typo guard)
def init_board() -> Board:
    return [
        list("rnbqkbnr"),
        list("pppppppp"),
        list("........"),
        list("........"),
        list("........"),
        list("........"),
        list("PPPPPPPP"),
        list("RNBQKBNR"),
    ]

def in_bounds(y:int,x:int)->bool: return 0<=y<8 and 0<=x<8

def piece_color(p:str)->Optional[str]:
    if p=='.': return None
    return 'white' if p.isupper() else 'black'

def print_board(board: Board):
    piece_symbols = {
        "K": "♔", "k": "♚",
        "Q": "♕", "q": "♛",
        "R": "♖", "r": "♜",
        "B": "♗", "b": "♝",
        "N": "♘", "n": "♞",
        "P": "♙", "p": "♟",
        ".": "."
    }
    for r in range(8):
        rank = 8 - r
        row_str = " ".join(piece_symbols.get(board[r][c], board[r][c]) for c in range(8))
        print(f"{rank} {row_str}")
    print("  a b c d e f g h")

def algebraic_to_idx(move: str) -> Optional[Tuple[Square, Square]]:
    # "e2e4" -> ((6,4),(4,4)). Trick: "e2e2" pour parser une case seule.
    if len(move) != 4: return None
    file_map = {'a':0,'b':1,'c':2,'d':3,'e':4,'f':5,'g':6,'h':7}
    c1,r1,c2,r2 = move[0],move[1],move[2],move[3]
    if c1 not in file_map or c2 not in file_map: return None
    try:
        x1 = file_map[c1]; y1 = 8 - int(r1)
        x2 = file_map[c2]; y2 = 8 - int(r2)
    except: return None
    if not (in_bounds(y1,x1) and in_bounds(y2,x2)): return None
    return (y1,x1),(y2,x2)

def idx_to_alg(y:int,x:int)->str: return "abcdefgh"[x] + str(8-y)

def find_king(board: Board, color: str) -> Square:
    target = 'K' if color=='white' else 'k'
    for y in range(8):
        for x in range(8):
            if board[y][x]==target:
                return (y,x)
    raise ValueError("King not found")

def square_attacked_by(board: Board, y:int, x:int, attacker_color:str) -> bool:
    # Pions
    if attacker_color=='white':
        for dy,dx in [(-1,-1),(-1,1)]:
            yy,xx=y+dy,x+dx
            if in_bounds(yy,xx) and board[yy][xx]=='P': return True
    else:
        for dy,dx in [(1,-1),(1,1)]:
            yy,xx=y+dy,x+dx
            if in_bounds(yy,xx) and board[yy][xx]=='p': return True
    # Cavaliers
    for dy,dx in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
        yy,xx=y+dy,x+dx
        if in_bounds(yy,xx):
            p=board[yy][xx]
            if attacker_color=='white' and p=='N': return True
            if attacker_color=='black' and p=='n': return True
    # Fous / Dames (diagonales)
    for dy,dx in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        yy,xx=y+dy,x+dx
        while in_bounds(yy,xx):
            p=board[yy][xx]
            if p!='.':
                if attacker_color=='white' and p in ('B','Q'): return True
                if attacker_color=='black' and p in ('b','q'): return True
                break
            yy+=dy; xx+=dx
    # Tours / Dames (lignes/colonnes)
    for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
        yy,xx=y+dy,x+dx
        while in_bounds(yy,xx):
            p=board[yy][xx]
            if p!='.':
                if attacker_color=='white' and p in ('R','Q'): return True
                if attacker_color=='black' and p in ('r','q'): return True
                break
            yy+=dy; xx+=dx
    # Roi
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dy==0 and dx==0: continue
            yy,xx=y+dy,x+dx
            if in_bounds(yy,xx):
                p=board[yy][xx]
                if attacker_color=='white' and p=='K': return True
                if attacker_color=='black' and p=='k': return True
    return False

def in_check(board: Board, color: str) -> bool:
    ky,kx = find_king(board, color)
    other = 'white' if color=='black' else 'black'
    return square_attacked_by(board, ky, kx, other)

class State:
    def __init__(self):
        self.board: Board = init_board()
        self.turn: str = 'white'
        # droits roque
        self.wkc = self.wqc = self.bkc = self.bqc = True
        # case en passant (destination de la prise) ou None
        self.en_passant: Optional[Square] = None
        # 50 coups: demi-coups depuis dernière capture ou coup de pion
        self.halfmove_clock: int = 0
        # numéro de coup (1 au départ, +1 après un coup noir)
        self.fullmove_number: int = 1
        # répétitions : clé de position -> compte
        self.position_counts: Dict[str,int] = {}

    def clone(self) -> 'State':
        s = State()
        s.board = [row[:] for row in self.board]
        s.turn = self.turn
        s.wkc, s.wqc, s.bkc, s.bqc = self.wkc, self.wqc, self.bkc, self.bqc
        s.en_passant = None if self.en_passant is None else (self.en_passant[0], self.en_passant[1])
        s.halfmove_clock = self.halfmove_clock
        s.fullmove_number = self.fullmove_number
        s.position_counts = dict(self.position_counts)
        return s

def move_piece(board: Board, a: Square, b: Square):
    y1,x1 = a; y2,x2 = b
    p = board[y1][x1]
    board[y2][x2] = p
    board[y1][x1] = '.'

def apply_promotion(board: Board, y:int, x:int, color:str, choice: Optional[str], interactive: bool):
    """Promote pawn on (y,x). choice in {'q','r','b','n'} or None.
       If interactive and choice is None, ask the user."""
    target = board[y][x]
    if color=='white' and y!=0: return
    if color=='black' and y!=7: return
    if target.upper()!='P': return

    def letter_from(c:str)->str:
        c = c.lower()
        mapping = {'q':'Q','r':'R','b':'B','n':'N'}
        ch = mapping.get(c,'Q')
        return ch if color=='white' else ch.lower()

    if interactive and choice is None:
        while True:
            raw = input("Promotion (q=♛, r=♜, b=♝, n=♞) [q]: ").strip().lower()
            if raw=='' or raw in ('q','r','b','n'):
                board[y][x] = letter_from(raw or 'q'); break
            print("Entrée invalide. Tape q/r/b/n.")
    else:
        board[y][x] = letter_from(choice or 'q')

def rook_positions_for(color:str)->Tuple[Square,Square]:
    # (tour côté roi, tour côté dame)
    return ((7,7),(7,0)) if color=='white' else ((0,7),(0,0))
def king_start_for(color:str)->Square: return (7,4) if color=='white' else (0,4)

def path_clear(board:Board, squares:Iterable[Square])->bool:
    return all(board[y][x]=='.' for y,x in squares)

def castling_rights_string(st: State)->str:
    s = ""
    if st.wkc: s += "K"
    if st.wqc: s += "Q"
    if st.bkc: s += "k"
    if st.bqc: s += "q"
    return s or "-"

def position_key(st: State)->str:
    rows = ["".join(r) for r in st.board]
    board_str = "/".join(rows)
    ep = "-" if st.en_passant is None else idx_to_alg(*st.en_passant)
    return f"{board_str}|{st.turn}|{castling_rights_string(st)}|{ep}"

def register_position(st: State):
    key = position_key(st)
    st.position_counts[key] = st.position_counts.get(key, 0) + 1

def legal_moves_for_piece(st: State, a: Square) -> List[Square]:
    board = st.board
    y,x = a
    p = board[y][x]
    if p=='.': return []
    color = piece_color(p)
    assert color is not None
    dir_pawn = -1 if color=='white' else 1
    moves: List[Square] = []

    if p.upper()=='P':
        y1 = y + dir_pawn
        if in_bounds(y1,x) and board[y1][x]=='.':
            moves.append((y1,x))
            start_row = 6 if color=='white' else 1
            y2 = y + 2*dir_pawn
            if y==start_row and board[y2][x]=='.':
                moves.append((y2,x))
        for dx in (-1,1):
            yy,xx = y+dir_pawn, x+dx
            if in_bounds(yy,xx):
                if board[yy][xx] != '.' and piece_color(board[yy][xx]) != color:
                    moves.append((yy,xx))
                if st.en_passant is not None and (yy,xx)==st.en_passant and board[yy][xx]=='.':
                    moves.append((yy,xx))
    elif p.upper()=='N':
        for dy,dx in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            yy,xx=y+dy,x+dx
            if in_bounds(yy,xx) and piece_color(board[yy][xx]) != color:
                moves.append((yy,xx))
    elif p.upper()=='B':
        for dy,dx in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            yy,xx=y+dy,x+dx
            while in_bounds(yy,xx):
                if board[yy][xx]=='.': moves.append((yy,xx))
                else:
                    if piece_color(board[yy][xx]) != color: moves.append((yy,xx))
                    break
                yy+=dy; xx+=dx
    elif p.upper()=='R':
        for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            yy,xx=y+dy,x+dx
            while in_bounds(yy,xx):
                if board[yy][xx]=='.': moves.append((yy,xx))
                else:
                    if piece_color(board[yy][xx]) != color: moves.append((yy,xx))
                    break
                yy+=dy; xx+=dx
    elif p.upper()=='Q':
        for dy,dx in [(-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)]:
            yy,xx=y+dy,x+dx
            while in_bounds(yy,xx):
                if board[yy][xx]=='.': moves.append((yy,xx))
                else:
                    if piece_color(board[yy][xx]) != color: moves.append((yy,xx))
                    break
                yy+=dy; xx+=dx
    elif p.upper()=='K':
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dy==0 and dx==0: continue
                yy,xx = y+dy, x+dx
                if in_bounds(yy,xx) and piece_color(board[yy][xx]) != color:
                    moves.append((yy,xx))
        # Roque
        if color=='white' and (y,x)==(7,4):
            if st.wkc and board[7][7]=='R' and path_clear(board, [(7,5),(7,6)]) \
               and not square_attacked_by(board,7,4,'black') \
               and not square_attacked_by(board,7,5,'black') \
               and not square_attacked_by(board,7,6,'black'):
                moves.append((7,6))
            if st.wqc and board[7][0]=='R' and path_clear(board, [(7,1),(7,2),(7,3)]) \
               and not square_attacked_by(board,7,4,'black') \
               and not square_attacked_by(board,7,3,'black') \
               and not square_attacked_by(board,7,2,'black'):
                moves.append((7,2))
        if color=='black' and (y,x)==(0,4):
            if st.bkc and board[0][7]=='r' and path_clear(board, [(0,5),(0,6)]) \
               and not square_attacked_by(board,0,4,'white') \
               and not square_attacked_by(board,0,5,'white') \
               and not square_attacked_by(board,0,6,'white'):
                moves.append((0,6))
            if st.bqc and board[0][0]=='r' and path_clear(board, [(0,1),(0,2),(0,3)]) \
               and not square_attacked_by(board,0,4,'white') \
               and not square_attacked_by(board,0,3,'white') \
               and not square_attacked_by(board,0,2,'white'):
                moves.append((0,2))

    # Filtrer (ne pas laisser son roi en échec). On simule avec promotion dame.
    legal: List[Square] = []
    for dest in moves:
        sim = st.clone()
        if not apply_move(sim, (y,x), dest, special_check_only=True):
            continue
        if not in_check(sim.board, color):
            legal.append(dest)
    return legal

def has_legal_moves(st: State, color: str) -> bool:
    for y in range(8):
        for x in range(8):
            p = st.board[y][x]
            if p!='.' and piece_color(p)==color:
                if legal_moves_for_piece(st, (y,x)):
                    return True
    return False

def update_castling_rights(st: State, a: Square, b: Square):
    y1,x1=a; y2,x2=b
    p = st.board[y2][x2]  # pièce après déplacement
    if p=='K': st.wkc = st.wqc = False
    if p=='k': st.bkc = st.bqc = False
    if (y1,x1)==(7,7) or (y2,x2)==(7,7): st.wkc = False
    if (y1,x1)==(7,0) or (y2,x2)==(7,0): st.wqc = False
    if (y1,x1)==(0,7) or (y2,x2)==(0,7): st.bkc = False
    if (y1,x1)==(0,0) or (y2,x2)==(0,0): st.bqc = False
    # si une tour de coin est capturée
    if (y2,x2)==(7,7) and st.board[7][7].islower(): st.wkc = False
    if (y2,x2)==(7,0) and st.board[7][0].islower(): st.wqc = False
    if (y2,x2)==(0,7) and st.board[0][7].isupper(): st.bkc = False
    if (y2,x2)==(0,0) and st.board[0][0].isupper(): st.bqc = False

def apply_move(st: State, a: Square, b: Square, special_check_only: bool=False, promotion_choice: Optional[str]=None) -> bool:
    """
    Applique un coup (gère roque/en passant/promotion). Si special_check_only=True,
    on n'interagit pas (promotion = dame automatique) et on ne touche pas aux compteurs.
    """
    board = st.board
    y1,x1 = a; y2,x2 = b
    p = board[y1][x1]
    if p=='.': return False
    color = piece_color(p)

    # Réinitialiser l'en-passant (sera recalculé si double pas)
    new_en_passant: Optional[Square] = None
    is_capture = board[y2][x2] != '.'
    is_pawn_move = (p.upper() == 'P')

    # Roque (roi se déplace de 2 colonnes)
    if p.upper()=='K' and y1==y2 and abs(x2-x1)==2:
        move_piece(board, a, b)
        if color=='white':
            if x2==6: move_piece(board, (7,7), (7,5))
            else:     move_piece(board, (7,0), (7,3))
            st.wkc = st.wqc = False
        else:
            if x2==6: move_piece(board, (0,7), (0,5))
            else:     move_piece(board, (0,0), (0,3))
    else:
        # Prise en passant
        if p.upper()=='P' and st.en_passant is not None and b==st.en_passant and board[y2][x2]=='.' and x2!=x1:
            move_piece(board, a, b)
            if color=='white':
                board[y2+1][x2] = '.'
            else:
                board[y2-1][x2] = '.'
            is_capture = True
        else:
            move_piece(board, a, b)

        # Promotion
        if p.upper()=='P' and ((color=='white' and y2==0) or (color=='black' and y2==7)):
            if special_check_only:
                board[y2][x2] = 'Q' if color=='white' else 'q'
            else:
                apply_promotion(board, y2, x2, color, promotion_choice, interactive=True)

        # En passant disponible si double pas
        if p.upper()=='P' and abs(y2 - y1) == 2:
            mid_y = (y1 + y2)//2
            new_en_passant = (mid_y, x1)

        update_castling_rights(st, a, b)

    # Mettre à jour l'en passant
    st.en_passant = new_en_passant

    if special_check_only:
        return True

    # 50 coups: reset si capture ou coup de pion, sinon +1
    if is_capture or is_pawn_move:
        st.halfmove_clock = 0
    else:
        st.halfmove_clock += 1

    # Changer le trait et incrémenter le numéro de coup après les noirs
    st.turn = 'black' if st.turn=='white' else 'white'
    if st.turn == 'white':
        st.fullmove_number += 1

    # Enregistrer la nouvelle position pour la nulle par répétition
    register_position(st)
    return True

def make_move_if_legal(st: State, a: Square, b: Square) -> bool:
    p = st.board[a[0]][a[1]]
    if p=='.' or piece_color(p)!=st.turn: return False
    legal = legal_moves_for_piece(st, a)
    if b not in legal: return False
    ok = apply_move(st, a, b, special_check_only=False)
    return ok

def game_status(st: State) -> Optional[str]:
    # Nulle 50 coups
    if st.halfmove_clock >= 100:
        return "Match nul (règle des 50 coups)."
    # Nulle trois répétitions
    if st.position_counts.get(position_key(st), 0) >= 3:
        return "Match nul (trois répétitions)."
    # Échec / mat / pat
    if in_check(st.board, st.turn):
        if not has_legal_moves(st, st.turn):
            return f"Échec et mat ! {'Noir' if st.turn=='white' else 'Blanc'} gagne."
        return "⚠️ Vous êtes en échec."
    else:
        if not has_legal_moves(st, st.turn):
            return "Pat ! Match nul."
    return None

def save_state(st: State, path: str):
    data = {
        "board": ["".join(r) for r in st.board],
        "turn": st.turn,
        "wkc": st.wkc, "wqc": st.wqc, "bkc": st.bkc, "bqc": st.bqc,
        "en_passant": None if st.en_passant is None else [st.en_passant[0], st.en_passant[1]],
        "halfmove_clock": st.halfmove_clock,
        "fullmove_number": st.fullmove_number,
        "position_counts": st.position_counts,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_state(path: str) -> State:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    st = State()
    st.board = [list(row) for row in d["board"]]
    st.turn = d["turn"]
    st.wkc, st.wqc, st.bkc, st.bqc = d["wkc"], d["wqc"], d["bkc"], d["bqc"]
    ep = d.get("en_passant")
    st.en_passant = None if ep is None else (ep[0], ep[1])
    st.halfmove_clock = int(d.get("halfmove_clock", 0))
    st.fullmove_number = int(d.get("fullmove_number", 1))
    st.position_counts = {str(k): int(v) for k,v in d.get("position_counts", {}).items()}
    return st

def game_help():
    print("Commandes :")
    print("  e2e4            -> jouer un coup")
    print("  moves e2        -> lister coups légaux depuis e2")
    print("  save [fichier]  -> sauvegarder (par défaut game.json)")
    print("  load [fichier]  -> charger (par défaut game.json)")
    print("  quit            -> quitter")
    print("Coups spéciaux : roque (e1g1/e1c1/e8g8/e8c8), en passant, promotion (q/r/b/n).")

def game_loop():
    st = State()
    register_position(st)  # position initiale
    while True:
        print_board(st.board)
        print(f"Trait aux {'Blancs' if st.turn=='white' else 'Noirs'}  |  Coup #{st.fullmove_number}  |  50-coups={st.halfmove_clock}")
        msg = game_status(st)
        if msg:
            print(msg)
            if msg.startswith("Échec et mat") or msg.startswith("Pat") or msg.startswith("Match nul"):
                break
        cmd = input(f"{'Blanc' if st.turn=='white' else 'Noir'} > ").strip()

        if cmd in ('h','help','?'):
            game_help(); continue
        if cmd in ('q','quit','exit'):
            print("Fin de partie."); break
        if cmd.startswith("moves "):
            sq = cmd.split(maxsplit=1)[1]
            m = algebraic_to_idx(sq+sq)
            if not m: print("Case invalide, ex: e2"); continue
            (y,x),_ = m
            if piece_color(st.board[y][x]) != st.turn:
                print("Pas votre pièce."); continue
            dests = legal_moves_for_piece(st, (y,x))
            if not dests: print("(aucun coup légal)")
            else:
                print("Coups possibles :", ", ".join(sq + idx_to_alg(dy,dx) for (dy,dx) in dests))
            continue
        if cmd.startswith("save"):
            parts = cmd.split(maxsplit=1)
            path = parts[1] if len(parts)==2 else "game.json"
            try:
                save_state(st, path)
                print(f"✅ Sauvegardé dans {os.path.abspath(path)}")
            except Exception as e:
                print("Erreur sauvegarde:", e)
            continue
        if cmd.startswith("load"):
            parts = cmd.split(maxsplit=1)
            path = parts[1] if len(parts)==2 else "game.json"
            try:
                st = load_state(path)
                print(f"✅ Chargé depuis {os.path.abspath(path)}")
            except Exception as e:
                print("Erreur chargement:", e)
            continue

        m = algebraic_to_idx(cmd)
        if not m:
            print("Format invalide. Exemple: e2e4, 'moves e2', 'save', 'load', 'quit'.")
            continue
        a,b = m
        if not make_move_if_legal(st, a, b):
            print("Coup illégal.")
            continue

if __name__ == "__main__":
    game_loop()
