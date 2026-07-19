import { Router, type IRouter } from "express";
import healthRouter from "./health";
import fingerprintRouter from "./fingerprint";

const router: IRouter = Router();

router.use(healthRouter);
router.use(fingerprintRouter);

export default router;
