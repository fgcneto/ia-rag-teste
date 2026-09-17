from dataclasses import dataclass
from enum import Enum
import hashlib,re
class Decision(str,Enum): ALLOW='ALLOW'; SECURITY_ATTACK='SECURITY_ATTACK'; PRIVACY_VIOLATION='PRIVACY_VIOLATION'; SECRET_REQUEST='SECRET_REQUEST'; TOO_LARGE='TOO_LARGE'
@dataclass(frozen=True)
class SecurityResult: decision:Decision; reason:str; redacted:str
INJECTION=[r'ignore (all|previous|prior).*(instruction|prompt)',r'ignore (todas?|qualquer).*(instru[cç][oõ]es?|regras?)',r'(revele|mostre).*(prompt do sistema|instru[cç][oõ]es internas)',r'jailbreak',r'bypass.*(guard|security|seguran[cç]a)']
SECRET=[r'(mostre|liste|extraia|revele|retorne|imprima).*(senha|password|token|api[_ -]?key|secret|chave privada|credential)']
PII_BULK=[r'(liste|mostre|extraia|exporte|retorne|imprima|dump).*(cpfs?|cns|pacientes?|nomes completos|e-?mails?)']
CPF=re.compile(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}'); EMAIL=re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
def _m(ps,t): return any(re.search(p,t,re.I|re.S) for p in ps)
def redact_pii(t): return EMAIL.sub('[EMAIL-MASCARADO]',CPF.sub('[CPF-MASCARADO]',t))
def inspect_question(t,max_chars):
    if len(t)>max_chars:return SecurityResult(Decision.TOO_LARGE,'Pergunta excede o tamanho permitido.',redact_pii(t[:max_chars]))
    if _m(INJECTION,t):return SecurityResult(Decision.SECURITY_ATTACK,'Prompt injection detectada.',redact_pii(t))
    if _m(SECRET,t):return SecurityResult(Decision.SECRET_REQUEST,'Solicitação de segredo.',redact_pii(t))
    if _m(PII_BULK,t):return SecurityResult(Decision.PRIVACY_VIOLATION,'Extração de dados pessoais.',redact_pii(t))
    return SecurityResult(Decision.ALLOW,'Pré-validação concluída.',redact_pii(t))
def output_guard(t): return redact_pii(t)
def question_hash(t): return hashlib.sha256(t.encode('utf-8',errors='ignore')).hexdigest()
NO_EVIDENCE_RESPONSE='Não encontrei informações suficientes nas fontes técnicas autorizadas para responder com segurança.'
PRIVACY_RESPONSE='Não posso fornecer, compilar ou extrair os dados pessoais ou sensíveis solicitados.'
SECURITY_RESPONSE='A solicitação contém instruções incompatíveis com as políticas deste assistente.'
SECRET_RESPONSE='Não posso revelar ou compilar credenciais, tokens, senhas, chaves privadas ou outros segredos.'
