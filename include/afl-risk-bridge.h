#ifndef __AFL_RISK_BRIDGE_H
#define __AFL_RISK_BRIDGE_H

#ifdef __cplusplus
extern "C" {
#endif

void __afl_risk_ins(unsigned int token);

#ifdef __cplusplus
}
#endif

/* User-visible compile-time switch:
   -DAFL_TRANSLATE_RISK_INS=1  => translate __POLAR_INS(...)
   -DAFL_TRANSLATE_RISK_INS=0  => compile it as no-op

   If the user does not specify this macro, default to enabled.
*/
#ifndef AFL_TRANSLATE_RISK_INS
#  define AFL_TRANSLATE_RISK_INS 1
#endif

#if AFL_TRANSLATE_RISK_INS
#  define __POLAR_INS(_X) \
     do { __afl_risk_ins((unsigned int)(_X)); } while (0)
#else
#  define __POLAR_INS(_X) \
     do { } while (0)
#endif

#endif