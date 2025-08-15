# chess_cli_v2.py — mini échecs console avec roque + en passant
# Commandes : coups "e2e4", aide "moves e2", "quit".
from typing import List, Tuple, Optional, Iterable

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
        list("RNBQKBNR"),
    ]

def in_bounds(y:int,x:int)->bool: return 0<=y<8 and 0<=x<8
def piece_color(p:str)->Optional[str]:
    if p=='.': return None
    return 'white' if p.isupper() else 'black'

def print_board(board: Board):
    for r in range(8):
        rank = 8 - r
        print(f"{rank} " + " ".join(board[r][c] if board[r][c] != '.' else '.' for c in range(8)))
    print("  a b c d e f g h")

def algebraic_to_idx(move: str) -> Optional[Tuple[Square, Square]]:
    # "e2e4" -> ((6,4),(4,4)). Hack: "e2e2" pour parser une case seule.
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
        # Droits de roque: wkc/wqc/bkc/bqc
        self.wkc = self.wqc = self.bkc = self.bqc = True
        # Case en passant possible (destination de la prise) ex: (2,4) ou None
        self.en_passant: Optional[Square] = None

    def clone(self) -> 'State':
        s = State()
        s.board = [row[:] for row in self.board]
        s.turn = self.turn
        s.wkc, s.wqc, s.bkc, s.bqc = self.wkc, self.wqc, self.bkc, self.bqc
        s.en_passant = None if self.en_passant is None else (self.en_passant[0], self.en_passant[1])
        return s

def move_piece(board: Board, a: Square, b: Square):
    y1,x1 = a; y2,x2 = b
    p = board[y1][x1]
    board[y2][x2] = p
    board[y1][x1] = '.'

def apply_promotion(board: Board, y:int, x:int):
    p = board[y][x]
    if p=='P' and y==0: board[y][x]='Q'
    if p=='p' and y==7: board[y][x]='q'

def rook_positions_for(color:str)->Tuple[Square,Square]:
    # (tour côté roi, tour côté dame)
    return ((7,7),(7,0)) if color=='white' else ((0,7),(0,0))

def king_start_for(color:str)->Square:
    return (7,4) if color=='white' else (0,4)

def path_clear(board:Board, squares:Iterable[Square])->bool:
    return all(board[y][x]=='.' for y,x in squares)

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
        # prises
        for dx in (-1,1):
            yy,xx = y+dir_pawn, x+dx
            if in_bounds(yy,xx):
                if board[yy][xx] != '.' and piece_color(board[yy][xx]) != color:
                    moves.append((yy,xx))
                # en passant
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
            # Petit roque: e1 -> g1 (f1,g1 vides, non attaqués)
            if st.wkc and board[7][4]=='K' and board[7][7]=='R':
                if path_clear(board, [(7,5),(7,6)]) \
                   and not square_attacked_by(board,7,4,'black') \
                   and not square_attacked_by(board,7,5,'black') \
                   and not square_attacked_by(board,7,6,'black'):
                    moves.append((7,6))
            # Grand roque: e1 -> c1 (d1,c1,b1 vides; e1,d1,c1 non attaqués)
            if st.wqc and board[7][4]=='K' and board[7][0]=='R':
                if path_clear(board, [(7,1),(7,2),(7,3)]) \
                   and not square_attacked_by(board,7,4,'black') \
                   and not square_attacked_by(board,7,3,'black') \
                   and not square_attacked_by(board,7,2,'black'):
                    moves.append((7,2))
        if color=='black' and (y,x)==(0,4):
            if st.bkc and board[0][4]=='k' and board[0][7]=='r':
                if path_clear(board, [(0,5),(0,6)]) \
                   and not square_attacked_by(board,0,4,'white') \
                   and not square_attacked_by(board,0,5,'white') \
                   and not square_attacked_by(board,0,6,'white'):
                    moves.append((0,6))
            if st.bqc and board[0][4]=='k' and board[0][0]=='r':
                if path_clear(board, [(0,1),(0,2),(0,3)]) \
                   and not square_attacked_by(board,0,4,'white') \
                   and not square_attacked_by(board,0,3,'white') \
                   and not square_attacked_by(board,0,2,'white'):
                    moves.append((0,2))

    # Filtrer: ne pas laisser son roi en échec. Utilise une simulation "apply_move".
    legal: List[Square] = []
    for dest in moves:
        sim = st.clone()
        if not apply_move(sim, a, dest, special_check_only=True):
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
    # Si un roi bouge: perd ses roques
    if p=='K':
        st.wkc = st.wqc = False
    if p=='k':
        st.bkc = st.bqc = False
    # Si une tour bouge: perd le côté correspondant
    if (y1,x1)==(7,7) or (y2,x2)==(7,7): st.wkc = False
    if (y1,x1)==(7,0) or (y2,x2)==(7,0): st.wqc = False
    if (y1,x1)==(0,7) or (y2,x2)==(0,7): st.bkc = False
    if (y1,x1)==(0,0) or (y2,x2)==(0,0): st.bqc = False
    # Si on capture une tour de coin, enlever le droit adverse
    if (y2,x2)==(7,7) and st.board[7][7].islower(): st.wkc = False
    if (y2,x2)==(7,0) and st.board[7][0].islower(): st.wqc = False
    if (y2,x2)==(0,7) and st.board[0][7].isupper(): st.bkc = False
    if (y2,x2)==(0,0) and st.board[0][0].isupper(): st.bqc = False

def apply_move(st: State, a: Square, b: Square, special_check_only: bool=False) -> bool:
    """
    Applique un coup sur l'état (avec roque/en passant/promo).
    special_check_only=True : on applique juste pour tester la légalité (usage dans le filtrage).
    Retourne True si réussi, False sinon (par ex. tentative de roque illégal à l’exécution).
    """
    board = st.board
    y1,x1 = a; y2,x2 = b
    p = board[y1][x1]
    if p=='.': return False
    color = piece_color(p)

    # Réinitialiser la case en passant; on recalculera éventuellement
    new_en_passant: Optional[Square] = None

    # Détection roque: roi se déplace de 2 colonnes
    if p.upper()=='K' and y1==y2 and abs(x2-x1)==2:
        # Vérif basique: la génération a déjà validé les cases/attaques,
        # on ne fait qu'appliquer le coup (déplacer aussi la tour).
        move_piece(board, a, b)
        if color=='white':
            if x2==6:  # petit roque: tour h1 -> f1
                move_piece(board, (7,7), (7,5))
            else:      # grand roque: tour a1 -> d1
                move_piece(board, (7,0), (7,3))
            st.wkc = st.wqc = False
        else:
            if x2==6:  # petit roque noir
                move_piece(board, (0,7), (0,5))
            else:      # grand roque noir
                move_piece(board, (0,0), (0,3))
            st.bkc = st.bqc = False
        # Promotion n/a pour roi
    else:
        # Prise en passant: pion se déplace en diagonale vers une case vide égale à st.en_passant
        did_en_passant = False
        if p.upper()=='P' and st.en_passant is not None and b==st.en_passant and board[y2][x2]=='.' and x2!=x1:
            move_piece(board, a, b)
            # supprimer le pion capturé derrière la case d'arrivée
            if color=='white':
                board[y2+1][x2] = '.'
            else:
                board[y2-1][x2] = '.'
            did_en_passant = True
        else:
            # Coup standard
            move_piece(board, a, b)

        # Promotion (auto dame)
        apply_promotion(board, y2, x2)

        # En passant disponible si pion avance de 2
        if p.upper()=='P' and abs(y2 - y1) == 2:
            mid_y = (y1 + y2)//2
            new_en_passant = (mid_y, x1)

        # MAJ droits de roque (y compris si capture d'une tour de coin)
        update_castling_rights(st, a, b)

    # Assigner la nouvelle cible en passant
    st.en_passant = new_en_passant

    if special_check_only:
        return True
    # Changer le trait
    st.turn = 'black' if st.turn=='white' else 'white'
    return True

def make_move_if_legal(st: State, a: Square, b: Square) -> bool:
    p = st.board[a[0]][a[1]]
    if p=='.' or piece_color(p)!=st.turn: return False
    legal = legal_moves_for_piece(st, a)
    if b not in legal: return False
    ok = apply_move(st, a, b, special_check_only=False)
    if not ok: return False
    return True

def game_status(st: State) -> Optional[str]:
    if in_check(st.board, st.turn):
        if not has_legal_moves(st, st.turn):
            return f"Échec et mat ! {'Noir' if st.turn=='white' else 'Blanc'} gagne."
        return "⚠️ Vous êtes en échec."
    else:
        if not has_legal_moves(st, st.turn):
            return "Pat ! Match nul."
    return None

def filestr(x:int)->str: return "abcdefgh"[x]
def sqstr(y:int,x:int)->str: return f"{filestr(x)}{8-y}"

def game_loop():
    st = State()
    while True:
        print_board(st.board)
        msg = game_status(st)
        if msg:
            print(msg)
            if msg.startswith("Échec et mat") or msg.startswith("Pat"):
                break
        prompt = f"{'Blanc' if st.turn=='white' else 'Noir'} ({'majuscules' if st.turn=='white' else 'minuscules'}) > "
        cmd = input(prompt).strip()
        if cmd in ('q','quit','exit'):
            print("Fin de partie.")
            break
        if cmd.startswith("moves "):
            sq = cmd.split()[1]
            m = algebraic_to_idx(sq+sq)
            if not m:
                print("Case invalide, ex: e2")
                continue
            (y,x),_ = m
            if piece_color(st.board[y][x]) != st.turn:
                print("Pas votre pièce.")
                continue
            dests = legal_moves_for_piece(st, (y,x))
            if not dests:
                print("(aucun coup légal)")
            else:
                print("Coups possibles depuis", sq, ":", ", ".join(sq + sqstr(dy,dx) for (dy,dx) in dests))
            continue

        m = algebraic_to_idx(cmd)
        if not m:
            print("Format invalide. Exemple: e2e4, ou 'moves e2', ou 'quit'.")
            continue
        a,b = m
        if not make_move_if_legal(st, a, b):
            print("Coup illégal.")
            continue

if __name__ == "__main__":
    game_loop()
